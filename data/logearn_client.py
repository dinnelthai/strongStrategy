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
        ["python", "/root/.hermes/skills/logearn/logearn-cli.py",
         "log-get-24h-signals", "--chain", str(chain)],
        capture_output=True, text=True,
        env={**os.environ, "LOGEARN_API_KEY": api_key},
        cwd="/root/.hermes/skills/logearn",
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[AWAKENING] JSON解析失败: {result.stdout[:200]}", file=sys.stderr)
        return []

    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff = now_ts - lookback_seconds
    awakening = []

    for token in data:
        if not isinstance(token, dict):
            continue

        sigs = token.get("all_signals_list", {}).get("breakout_volume_10x_list", [])
        if not sigs:
            continue

        for sig in sigs:
            created = sig.get("created_time", 0)
            if created < cutoff:
                continue

            open_p  = sig.get("current_open_price", 0)
            close_p = sig.get("current_close_price", 0)

            # 强苏醒：close/open > 2
            if open_p > 0 and close_p / open_p > 2:
                awakening.append({
                    "token_address":  token.get("token_address"),
                    "symbol":         token.get("symbol"),
                    "signal_time":    sig.get("signal_time"),
                    "created_time":   created,
                    "open_price":     open_p,
                    "close_price":    close_p,
                    "volume_ratio":   sig.get("volume_ratio", 0),
                    "chain":          chain,
                })

    return awakening


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
        ["python", "/root/.hermes/skills/logearn/logearn-cli.py",
         "log-get-kline",
         "--token",   token_address,
         "--chain",   str(chain),
         "--interval", "60",    # 1分钟
         "--size",    str(size)],
        capture_output=True, text=True,
        env={**os.environ, "LOGEARN_API_KEY": api_key},
        cwd="/root/.hermes/skills/logearn",
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
