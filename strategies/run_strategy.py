#!/usr/bin/env python3
"""
强势盘策略 - 主轮询脚本
=========================

每分钟执行一次：
  1. 从 LogEarn 获取最新苏醒信号，加入轮询池
  2. 清理超期信号
  3. 轮询池中每个CA，获取1分钟K线
  4. 计算 AO/AC/VWAP，满足条件则买入

用法:
    LOGEARN_API_KEY=sk_xxx  python3 strategies/run_strategy.py

Cron 配置（每1分钟）:
    * * * * *  LOGEARN_API_KEY=sk_xxx  python3 /root/strongStrategy/strategies/run_strategy.py
"""

import os, sys, time, asyncio, threading, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from data.logearn_client import get_awakening_signals, get_kline_1m, merge_klines
from strategies.awakening_strategy import check_entry_conditions, check_static_conditions
from monitor.pool_manager import AwakeningPool


# ============ 策略参数 ============
API_KEY          = os.environ.get("LOGEARN_API_KEY", "")
CHAIN            = int(os.environ.get("CHAIN", "3"))
SIGNAL_INTERVAL  = 60     # 信号拉取间隔（秒）
POOL_MAX_AGE     = 1800   # 信号最大存活（30分钟）
KLINE_MIN        = 60      # 最少拉取根数（满足 AO/AC 计算）
KLINE_MAX        = 21600   # 拉取上限（API 侧实际能返回多少就多少）
KLINE_DELTA      = 3       # 每分钟增量补齐根数（覆盖最新 3 根即可）
SCAN_INTERVAL    = 5       # 池子为空时的等待间隔（秒）


# ============ 日志配置 ============

LOG_DIR  = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "strategy.log")
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)

logger = logging.getLogger("strategy")
logger.setLevel(logging.DEBUG)
logger.addHandler(_file_handler)
logger.addHandler(_console_handler)


# ============ 后台线程：每 60s 拉信号入池 ============

def signal_fetcher(pool: AwakeningPool):
    """后台线程：每 SIGNAL_INTERVAL 秒拉取苏醒信号，加入池子。"""
    while True:
        try:
            signals = get_awakening_signals(API_KEY, chain=CHAIN, lookback_seconds=3600)
            new_count = 0
            for sig in signals:
                ca  = sig["token_address"]
                sym = sig["symbol"]
                ok, reason = check_static_conditions(sig)
                if not ok:
                    logger.debug(f"[过滤] {sym} 被淘汰：{reason}")
                    continue

                added = pool.add(ca, sym,
                                 signal_time=sig.get("signal_time", 0),
                                 chain=sig.get("chain", CHAIN),
                                 meta=sig)
                if added:
                    new_count += 1
                    logger.info(f"[信号] 新苏醒 {sym} ({ca[:12]}...)")

            expired = pool.cleanup_expired()
            logger.info(f"[信号] 本轮新增 {new_count} 个 | 过期清理 {len(expired)} 个 | 池内 {len(pool)} 个")
        except Exception as e:
            logger.error(f"[信号] 拉取失败: {e}", exc_info=True)

        time.sleep(SIGNAL_INTERVAL)


# ============ 异步消费：单个 token 检查 ============

def _kline_size_for(token_meta: dict) -> int:
    """
    从代币首笔交易（swap_begin_time）起算，拉取全部历史 1 分钟 K 线。
    上限 KLINE_MAX = 15天，下限 KLINE_MIN = 60根。
    """
    begin_ts = float(token_meta.get("swap_begin_time") or 0)
    if begin_ts <= 0:
        return KLINE_MAX
    bars = int((time.time() - begin_ts) / 60) + 1
    return max(KLINE_MIN, min(bars, KLINE_MAX))


async def check_one(item, pool: AwakeningPool):
    """
    异步检查单个 token，两阶段 K 线拉取：
      - 无缓存（首次入池）：全量拉取所有历史 K 线，写入 item.klines
      - 有缓存（后续每轮）：增量拉取最新 KLINE_DELTA 根，merge 补齐缓存
    """
    sym = item.symbol
    ca  = item.token_address
    try:
        if not item.klines:
            size = _kline_size_for(item.meta)
            new_bars = await asyncio.to_thread(
                get_kline_1m, API_KEY, ca, chain=item.chain, size=size
            )
            item.klines = new_bars
            logger.info(f"[K线] {sym} ({ca[:12]}...) 首次全量 {len(new_bars)} 根")
        else:
            new_bars = await asyncio.to_thread(
                get_kline_1m, API_KEY, ca, chain=item.chain, size=KLINE_DELTA
            )
            item.klines = merge_klines(item.klines, new_bars)

        if not item.klines:
            return

        klen = len(item.klines)
        logger.debug(f"── {sym} ({ca}) K线={klen}根 ──")

        ok, reason = check_entry_conditions(item.klines, item.meta)
        if ok:
            logger.warning(f"[买入信号] {sym} ({ca}) | {reason}")
            # TODO: 接入 Phase2 买入逻辑
            # await phase2_buy(token_address=ca, amount=...)
            pool.remove(ca)
        else:
            logger.debug(f"  → 未命中: {reason}")
    except Exception as e:
        logger.error(f"[错误] 检查 {sym} ({ca}) 时失败: {e}", exc_info=True)


# ============ 异步主循环：并发消费池子 ============

async def scan_loop(pool: AwakeningPool):
    """
    异步主循环：每 60s 一轮，并发检查池内所有 token。
    - 首次入池的 token：全量拉历史 K 线
    - 已有缓存的 token：增量补最新 3 根
    """
    while True:
        items = pool.get_all()

        if not items:
            await asyncio.sleep(SCAN_INTERVAL)
            continue

        t0 = time.time()
        await asyncio.gather(*[check_one(item, pool) for item in items])
        elapsed = time.time() - t0
        logger.info(f"[扫描] 本轮并发检查 {len(items)} 个，耗时 {elapsed:.1f}s")

        # 每轮结束等满 60s，与信号拉取周期对齐
        wait = max(0, SIGNAL_INTERVAL - elapsed)
        if wait > 0:
            await asyncio.sleep(wait)


async def amain():
    if not API_KEY:
        logger.error("LOGEARN_API_KEY not set")
        sys.exit(1)

    pool = AwakeningPool(max_age_seconds=POOL_MAX_AGE)

    # 后台线程：每 60s 拉信号
    t = threading.Thread(target=signal_fetcher, args=(pool,), daemon=True)
    t.start()
    logger.info(f"[启动] 信号拉取线程已启动（每{SIGNAL_INTERVAL}s）")
    logger.info(f"[启动] 异步扫描主循环已启动，日志文件：{LOG_FILE}")

    await scan_loop(pool)


if __name__ == "__main__":
    asyncio.run(amain())
