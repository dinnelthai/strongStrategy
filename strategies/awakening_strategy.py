"""
强势盘策略 - 核心策略引擎
==============================

买入条件（全部满足）：
  1. AO > 0（动量向上）
  2. AC > 0（加速度正向）
  3. 连续 3 根 K 线收红（收盘 > 开盘）
  4. 最新收盘价 > VWAP（价格处于均线上方）

K线周期：1 分钟
信号来源：LogEarn 苏醒信号（breakout_volume_10x）
"""

from .indicators.vwap import calc_vwap
from .indicators.ao_ac import calc_ao, calc_ac

# K线颜色判断
def is_green(candle) -> bool:
    """收盘 > 开盘 = 绿色K线（阳线）"""
    return candle["close"] > candle["open"]


def check_entry_conditions(candles_1m: list) -> tuple[bool, str]:
    """
    检查是否满足买入条件。

    Args:
        candles_1m: 按时间升序排列的1分钟K线列表，每条包含 open/high/low/close/volume

    Returns:
        (是否满足, 原因描述)
    """
    if len(candles_1m) < 4:
        return False, f"K线不足（需要至少4根，当前{len(candles_1m)}根）"

    # 取最近4根K线（用于计算和判断）
    recent = candles_1m[-4:]

    # 条件1: 连续3根绿色K线
    last_3 = recent[-3:]
    if not all(is_green(c) for c in last_3):
        green_count = sum(1 for c in last_3 if is_green(c))
        return False, f"连续K线不满足（需要3根绿，当前{green_count}根绿）"

    # 条件2: AO > 0
    closes = [c["close"] for c in candles_1m]
    highs  = [c["high"]  for c in candles_1m]
    lows   = [c["low"]   for c in candles_1m]
    volumes = [c["volume"] for c in candles_1m]

    ao = calc_ao(closes, highs, lows)
    if ao <= 0:
        return False, f"AO <= 0（当前值:{ao:.6f}）"

    # 条件3: AC > 0
    ac = calc_ac(closes, highs, lows)
    if ac <= 0:
        return False, f"AC <= 0（当前值:{ac:.6f}）"

    # 条件4: 最新收盘 > VWAP
    vwap = calc_vwap(closes, highs, lows, volumes)
    last_close = closes[-1]
    if last_close <= vwap:
        return False, f"价格未站上VWAP（收盘:{last_close:.6f} <= VWAP:{vwap:.6f}）"

    return True, f"买入信号满足 | AO:{ao:.6f} AC:{ac:.6f} 收盘:{last_close:.6f} VWAP:{vwap:.6f}"
