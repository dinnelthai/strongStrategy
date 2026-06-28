"""
VWAP (Volume Weighted Average Price)
=====================================

VWAP = Σ(典型价格 × 成交量) / Σ(成交量)
典型价格 = (High + Low + Close) / 3

使用最近 period 根K线计算（默认全量）
"""

import numpy as np


def calc_vwap(closes: list, highs: list, lows: list, volumes: list, period: int = None) -> float:
    """
    计算 VWAP

    Args:
        closes:  收盘价列表
        highs:   最高价列表
        lows:    最低价列表
        volumes: 成交量列表
        period:  计算窗口（None = 全量）

    Returns:
        VWAP 值（标量）
    """
    n = len(closes)
    if n == 0 or len(highs) != n or len(lows) != n or len(volumes) != n:
        return 0.0

    if period is not None and period > 0:
        closes  = closes[-period:]
        highs   = highs[-period:]
        lows    = lows[-period:]
        volumes = volumes[-period:]

    # 典型价格
    typical = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]

    # 分子: Σ(典型价格 × 成交量)
    numerator = sum(t * v for t, v in zip(typical, volumes))
    # 分母: Σ(成交量)
    denominator = sum(volumes)

    if denominator == 0:
        return 0.0

    return numerator / denominator
