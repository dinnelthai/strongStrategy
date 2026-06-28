"""
LogEarn 数据获取客户端
=======================

职责：
  1. 从 LogEarn API 获取苏醒信号（breakout_volume_10x）
  2. 从 LogEarn API 获取 1 分钟 K 线数据

苏醒信号 → 加入轮询池
K线数据   → 计算指标 → 判断是否满足买入条件
"""

import json, subprocess, os, sys
from datetime import datetime, timezone
from typing import Optional

_CLI_PATH = os.environ.get(
    "LOGEARN_CLI_PATH",
    "/Users/leon/logearn_kit/logearn-skills/logearn-cli.py"
)
_CLI_CWD  = os.path.dirname(_CLI_PATH)


# ============ 苏醒信号获取 ============

def get_awakening_signals(api_key: str, chain: int = 3, lookback_seconds: int = 7200) -> list[dict]:
    """
    获取最近 lookback_seconds 内的苏醒信号（breakout_volume_10x）。

    筛选条件：close/open > 2（强苏醒）

    Args:
        api_key:          LogEarn API Key
        chain:            链ID（3=Solana，56=BSC）
        lookback_seconds: 回看秒数（默认2小时）

    Returns:
        苏醒信号代币列表，每条包含 token 信息 + 苏醒信号详情
    """
    result = subprocess.run(
        ["python3", _CLI_PATH,
         "log-get-24h-signals", "--chain", str(chain)],
        capture_output=True, text=True,
        env={**os.environ, "LOGEARN_API_KEY": api_key},
        cwd=_CLI_CWD,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[AWAKENING] JSON解析失败: {result.stdout[:200]}", file=sys.stderr)
        return []

    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff = now_ts - lookback_seconds
    awakening = []

    for chain_tokens in data:
        if not isinstance(chain_tokens, list):
            continue
        for token in chain_tokens:
            if not isinstance(token, dict):
                continue

            sigs = token.get("all_signals_list", {}).get("breakout_volume_10x_list", [])
            if not sigs:
                continue

            for sig in sigs:
                created = sig.get("created_time", 0)
                if created < cutoff:
                    continue

                volume_ratio = sig.get("volume_ratio", 0) or 0

                # 强苏醒：成交量倍数 >= 10（volume_ratio = 当前量/休眠均量）
                if volume_ratio >= 10:
                    tag = token.get("tag_users_holding_percent") or {}
                    awakening.append({
                        "token_address":       token.get("token_address"),
                        "symbol":              token.get("symbol"),
                        "signal_time":         sig.get("signal_time"),
                        "created_time":        created,
                        "volume_ratio":        volume_ratio,
                        "current_volume":      sig.get("current_volume", 0),
                        "avg_history_volume":  sig.get("avg_history_volume", 0),
                        "chain":               token.get("chain", chain),
                        # --- token_meta fields for strategy ---
                        "platform":            token.get("platform", ""),
                        "swap_begin_time":     token.get("swap_begin_time", 0),
                        "launch_time":         token.get("launch_time", 0),
                        "launch_time_duration": token.get("launch_time_duration", 0),
                        "buyer_count_d1":      token.get("buyer_count_d1", 0),
                        "buy_tx_count_d1":     token.get("buy_tx_count_d1", 0),
                        "shit_volume":         tag.get("shit_volume", 0),
                        "new_volume":          tag.get("new_volume", 0),
                        "smart_volume":        tag.get("smart_volume", 0),
                        "whale_volume":        tag.get("whale_volume", 0),
                        "scam_volume":         tag.get("scam_volume", 0),
                    })

    return awakening


# ============ K线合并工具 ============

def merge_klines(cached: list, new_bars: list, max_size: int = 60) -> list:
    """
    将增量 K 线合并进缓存。
    - 以 time 为 key 去重（新 bar 覆盖旧 bar，更新最新价格）
    - 按时间升序排列
    - 只保留最后 max_size 根
    """
    by_time = {c["time"]: c for c in cached}
    for bar in new_bars:
        by_time[bar["time"]] = bar
    merged = sorted(by_time.values(), key=lambda x: x["time"])
    return merged[-max_size:]


# ============ K线数据获取 ============

def get_kline_1m(api_key: str, token_address: str, chain: int = 3, size: int = 60) -> list[dict]:
    """
    获取 1 分钟 K 线数据。

    Args:
        api_key:        LogEarn API Key
        token_address:  代币合约地址
        chain:          链ID
        size:           K线条数（默认60条 = 最近60分钟）

    Returns:
        K线列表，每条: {time, open, high, low, close, volume}
    """
    result = subprocess.run(
        ["python3", _CLI_PATH,
         "log-get-kline",
         "--token",    token_address,
         "--chain",    str(chain),
         "--interval", "60",
         "--size",     str(size)],
        capture_output=True, text=True,
        env={**os.environ, "LOGEARN_API_KEY": api_key},
        cwd=_CLI_CWD,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[KLINE] JSON解析失败: {result.stdout[:200]}", file=sys.stderr)
        return []

    # 解析 K线（字段可能是 openU/closeU 或 open/close）
    candles = []
    for item in data if isinstance(data, list) else []:
        candles.append({
            "time":   item.get("time", 0),
            "open":   float(item.get("openU") or item.get("open") or 0),
            "high":   float(item.get("highU") or item.get("high") or 0),
            "low":    float(item.get("lowU")  or item.get("low")  or 0),
            "close":  float(item.get("closeU") or item.get("close") or 0),
            "volume": float(item.get("volume") or 0),
        })

    # 按时间升序
    candles.sort(key=lambda x: x["time"])
    return candles
