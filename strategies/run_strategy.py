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

import os, sys, time, json
from datetime import datetime

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from data.logearn_client import get_awakening_signals, get_kline_1m
from strategies.awakening_strategy import check_entry_conditions
from monitor.pool_manager import AwakeningPool


# ============ 策略参数 ============
API_KEY       = os.environ.get("LOGEARN_API_KEY", "")
CHAIN         = int(os.environ.get("CHAIN", "3"))
POLL_INTERVAL = 60        # 轮询间隔（秒）
POOL_MAX_AGE  = 1800      # 信号最大存活（30分钟）
KLINE_SIZE    = 60        # 获取最近60根1分钟K线
POLL_BATCH    = 10        # 每轮最多检查多少个CA


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    if not API_KEY:
        log("ERROR: LOGEARN_API_KEY not set")
        sys.exit(1)

    pool = AwakeningPool(max_age_seconds=POOL_MAX_AGE)

    while True:
        loop_start = time.time()
        log("========== 策略轮询开始 ==========")

        # 1. 获取最新苏醒信号，加入池
        try:
            signals = get_awakening_signals(API_KEY, chain=CHAIN, lookback_seconds=7200)
            new_count = 0
            for sig in signals:
                ca  = sig["token_address"]
                sym = sig["symbol"]
                pool.add(ca, sym, signal_time=sig.get("signal_time", 0), chain=sig.get("chain", CHAIN))
                new_count += 1
                log(f"  [新苏醒] {sym} ({ca[:12]}...) close/open={sig['close_price']/sig['open_price']:.1f}x")
            log(f"  新增信号: {new_count} 个，池内总计: {len(pool)} 个")
        except Exception as e:
            log(f"  [错误] 获取苏醒信号失败: {e}")

        # 2. 清理超期信号
        expired = pool.cleanup_expired()
        if expired:
            log(f"  [清理] 超期移除: {len(expired)} 个")

        # 3. 轮询池中CA，计算指标
        checked = 0
        for _ in range(POLL_BATCH):
            item = pool.rotate()
            if item is None:
                break
            checked += 1

            try:
                # 获取1分钟K线
                candles = get_kline_1m(API_KEY, item.token_address, chain=item.chain, size=KLINE_SIZE)
                if not candles:
                    continue

                # 检查买入条件
                ok, reason = check_entry_conditions(candles)
                if ok:
                    log(f"  [买入信号] {item.symbol} | {reason}")
                    # TODO: 这里接入 Phase2 买入逻辑
                    # phase2_buy(token_address=item.token_address, amount=...)
                    pool.remove(item.token_address)  # 成交后移除
                else:
                    log(f"  [扫描] {item.symbol}: {reason}")
            except Exception as e:
                log(f"  [错误] 检查 {item.symbol} 时失败: {e}")

        log(f"  本轮检查: {checked} 个，池内剩余: {len(pool)} 个")
        log("========== 轮询结束 ==========")

        elapsed = time.time() - loop_start
        sleep_time = max(0, POLL_INTERVAL - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()
