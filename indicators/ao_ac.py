"""
AO (Awesome Oscillator) & AC (Acceleration)
==========================================

AO = SMA(中位价, 5) - SMA(中位价, 34)
    中位价 = (High + Low) / 2

AC = SMA(AO, 5)
"""

import numpy as np


def calc_median_price(highs: list, lows: list) -> list:
    """中位价 = (High + Low) / 2"""
    return [(h + l) / 2 for h, l in zip(highs, lows)]


def sma(data: list, period: int) -> float | None:
    """简单移动平均，取最近 period 个值的均值"""
    if len(data) < period:
        return None
    return sum(data[-period:]) / period


def calc_ao(closes: list, highs: list, lows: list) -> float:
    """
    计算 AO（Awesome Oscillator）
    AO = SMA(中位价, 5) - SMA(中位价, 34)
    返回最新 AO 值（一个标量）
    """
    medians = calc_median_price(highs, lows)
    if len(medians) < 34:
        return 0.0

    sma5  = sma(medians, 5)
    sma34 = sma(medians, 34)

    if sma5 is None or sma34 is None:
        return 0.0
    return sma5 - sma34


def calc_ac(closes: list, highs: list, lows: list) -> float:
    """
    计算 AC（Acceleration）

    AC = AO 的 5 周期 SMA（对 AO 序列求 SMA）
    先计算 AO 序列，再对 AO 序列取 5 周期 SMA

    注意：AC 的周期数比 AO 短，所以需要更多K线数据才能计算
    需要至少 34 + 5 - 1 = 38 根K线
    """
    if len(closes) < 38:
        return 0.0

    # 构建 AO 序列（每根K线对应一个 AO 值）
    ao_sequence = []
    for i in range(34, len(closes)):
        window_medians = [(highs[j] + lows[j]) / 2 for j in range(i - 34, i + 1)]
        sma5  = sum(window_medians[-5:])  / 5
        sma34 = sum(window_medians)       / 34
        ao_sequence.append(sma5 - sma34)

    if len(ao_sequence) < 5:
        return 0.0

    # AC = AO 的 5 周期 SMA
    return sum(ao_sequence[-5:]) / 5
