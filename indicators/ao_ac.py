"""
AO (Awesome Oscillator) & AC (Acceleration)
==========================================

AO = SMA(中位价, 5) - SMA(中位价, 34)
    中位价 = (High + Low) / 2

AC = SMA(AO, 5)
"""

from typing import Optional


def calc_median_price(highs: list, lows: list) -> list:
    """中位价 = (High + Low) / 2"""
    return [(h + l) / 2 for h, l in zip(highs, lows)]


def sma(data: list, period: int) -> Optional[float]:
    """简单移动平均，取最近 period 个值的均值"""
    if len(data) < period:
        return None
    return sum(data[-period:]) / period


def calc_ao_series(highs: list, lows: list) -> list:
    """
    返回完整 AO 序列（升序，最新值在末尾）。
    每个位置从 index=33 开始，对应一根 K 线的 AO 值。
    """
    medians = calc_median_price(highs, lows)
    n = len(medians)
    if n < 34:
        return []
    result = []
    for i in range(33, n):
        sma5_val  = sum(medians[i - 4  : i + 1]) / 5
        sma34_val = sum(medians[i - 33 : i + 1]) / 34
        result.append(sma5_val - sma34_val)
    return result


def calc_ao(closes: list, highs: list, lows: list) -> float:
    """
    返回最新 AO 值（标量）。
    AO = SMA(中位价, 5) - SMA(中位价, 34)
    """
    series = calc_ao_series(highs, lows)
    return series[-1] if series else 0.0


def calc_ac(closes: list, highs: list, lows: list) -> float:
    """
    返回最新 AC 值（标量）。
    AC = AO - SMA(AO, 5)  ← 标准比尔威廉姆斯公式
    需要至少 34 + 5 - 1 = 38 根K线
    """
    series = calc_ao_series(highs, lows)
    if len(series) < 5:
        return 0.0
    ao_now = series[-1]
    sma5_val = sum(series[-5:]) / 5
    return ao_now - sma5_val
