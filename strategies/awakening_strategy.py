"""
强势盘策略 - 核心策略引擎
==============================

过滤条件（按顺序，任一不满足即返回 False）：
  1. 平台白名单（Pump / Mayhem）
  2. 年龄 ≤ 15 天
  3. 已毕业到外盘 + 毕业后 ≥ 120 分钟
  4. 垃圾钱包占比 < 5%
  5. 新钱包占比 < 70%
  6. 24h 买入地址数 > 50
  7. 成本线偏差 > 2%（收盘价高于 VWAP 2% 以上）
  8. AO 最近 3 根全 > 0 且递增
  9. AC > 0 且 AC[0] > AC[1]（加速）

K线周期：1 分钟
信号来源：LogEarn 苏醒信号（breakout_volume_10x）
"""

import time
from typing import Optional
from indicators.vwap import calc_vwap
from indicators.ao_ac import calc_ao_series

# 平台白名单（Pump.fun / Mayhem）
ALLOW_PLATFORMS = {
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "mayhem",
}

# 可调参数
AGE_MAX_DAYS          = 15
GRADUATION_MIN_SEC    = 7200   # 毕业后至少 120 分钟
SHIT_VOLUME_MAX_PCT   = 5
NEW_VOLUME_MAX_PCT    = 70
BUY_TX_MIN_D1         = 50
COST_DEVIATION_MIN_PCT = 2.0   # 收盘高于 VWAP 的最低偏差 %
AO_LOOKBACK           = 3      # 连续 N 根 AO 需 > 0 且递增


def _num(x) -> float:
    try:
        v = float(x)
        return v if v == v else 0.0  # NaN guard
    except (TypeError, ValueError):
        return 0.0


def check_entry_conditions(candles_1m: list, token_meta: dict) -> tuple[bool, str]:
    """
    检查是否满足买入条件。

    Args:
        candles_1m:  按时间升序排列的1分钟K线列表，每条包含 open/high/low/close/volume
        token_meta:  从 LogEarn 取得的代币元数据（platform, swap_begin_time, 等）

    Returns:
        (是否满足, 原因描述)
    """
    symbol = token_meta.get("symbol", "UNKNOWN")

    # ------------------------------------------------------------------
    # 1. 平台白名单
    # ------------------------------------------------------------------
    platform = token_meta.get("platform", "")
    if platform not in ALLOW_PLATFORMS:
        return False, f"平台不在白名单：{platform}"

    # ------------------------------------------------------------------
    # 2. 年龄 ≤ 15 天
    # ------------------------------------------------------------------
    now_ts     = time.time()
    launch_ts  = _num(token_meta.get("swap_begin_time", 0))
    age_days   = (now_ts - launch_ts) / 86400 if launch_ts > 0 else float("inf")
    if launch_ts <= 0 or age_days > AGE_MAX_DAYS:
        return False, f"年龄不符（{age_days:.1f}天，上限{AGE_MAX_DAYS}天）"

    # ------------------------------------------------------------------
    # 3. 已毕业到外盘 + 毕业后 ≥ 120 分钟
    # ------------------------------------------------------------------
    if not (_num(token_meta.get("launch_time_duration", 0)) > 0):
        return False, "还在内盘曲线上，未毕业到外盘"

    m_launch_ts = _num(token_meta.get("launch_time", 0))
    if m_launch_ts > 0:
        after_launch = now_ts - m_launch_ts
        if after_launch < GRADUATION_MIN_SEC:
            return False, f"外盘毕业不足{GRADUATION_MIN_SEC//60}分钟（{after_launch:.0f}秒）"

    # ------------------------------------------------------------------
    # 4. 垃圾钱包占比 < 5%
    # ------------------------------------------------------------------
    shit_vol = _num(token_meta.get("shit_volume", 0))
    if shit_vol >= SHIT_VOLUME_MAX_PCT:
        return False, f"垃圾钱包占比过高：{shit_vol:.1f}%"

    # ------------------------------------------------------------------
    # 5. 新钱包占比 < 70%
    # ------------------------------------------------------------------
    new_vol = _num(token_meta.get("new_volume", 0))
    if new_vol >= NEW_VOLUME_MAX_PCT:
        return False, f"新钱包占比过高：{new_vol:.1f}%"

    # ------------------------------------------------------------------
    # 6. 24h 买入地址数 > 50（buyer_count_d1 = 唯一买入地址数）
    # ------------------------------------------------------------------
    buyer_count = _num(token_meta.get("buyer_count_d1", 0))
    if buyer_count <= BUY_TX_MIN_D1:
        return False, f"24h买入地址不足：{buyer_count:.0f}（需>{BUY_TX_MIN_D1}）"

    # ------------------------------------------------------------------
    # K 线数据准备
    # ------------------------------------------------------------------
    if len(candles_1m) < 38:
        return False, f"K线不足（需38根，当前{len(candles_1m)}根）"

    closes  = [c["close"]  for c in candles_1m]
    highs   = [c["high"]   for c in candles_1m]
    lows    = [c["low"]    for c in candles_1m]
    volumes = [c["volume"] for c in candles_1m]

    # ------------------------------------------------------------------
    # 7. 成本线偏差 > 2%（收盘价 > VWAP + 2%）
    # ------------------------------------------------------------------
    vwap = calc_vwap(closes, highs, lows, volumes)
    last_close = closes[-1]
    deviation_pct = (last_close - vwap) / vwap * 100 if vwap > 0 else 0.0
    if deviation_pct <= COST_DEVIATION_MIN_PCT:
        return False, f"成本线偏差不足：{deviation_pct:.2f}%（需>{COST_DEVIATION_MIN_PCT}%）"

    # ------------------------------------------------------------------
    # 8. AO：最近 3 根全 > 0 且严格递增（ao0 > ao1 > ao2）
    # ------------------------------------------------------------------
    ao_series = calc_ao_series(highs, lows)
    if len(ao_series) < AO_LOOKBACK + 4:  # 保证有足够的 AC 窗口
        return False, f"AO序列不足（{len(ao_series)}根）"

    ao0, ao1, ao2 = ao_series[-1], ao_series[-2], ao_series[-3]
    if not (ao0 > 0 and ao1 > 0 and ao2 > 0):
        return False, f"AO未全部>0：[{ao0:.4f},{ao1:.4f},{ao2:.4f}]"
    if not (ao0 > ao1 > ao2):
        return False, f"AO未递增：[{ao0:.4f},{ao1:.4f},{ao2:.4f}]"

    # ------------------------------------------------------------------
    # 9. AC：ac0 > 0 且 ac0 > ac1（加速向上）
    #    AC(i) = AO[i] - SMA(AO[i-4..i])
    # ------------------------------------------------------------------
    def _ac_at(idx_from_end: int) -> Optional[float]:
        """idx_from_end=0 → 最新，1 → 上一根"""
        pos = len(ao_series) - 1 - idx_from_end
        if pos - 4 < 0:
            return None
        window = ao_series[pos - 4 : pos + 1]
        return ao_series[pos] - sum(window) / 5

    ac0 = _ac_at(0)
    ac1 = _ac_at(1)
    if ac0 is None or ac1 is None:
        return False, "AC数据不足"
    if not (ac0 > 0 and ac0 > ac1):
        return False, f"AC条件不满足：ac0={ac0:.4f} ac1={ac1:.4f}"

    # ------------------------------------------------------------------
    # 全部通过
    # ------------------------------------------------------------------
    return True, (
        f"[命中] {symbol} | "
        f"年龄={age_days:.1f}天 | "
        f"成本偏差={deviation_pct:.2f}% | "
        f"AO=[{ao0:.2f},{ao1:.2f},{ao2:.2f}] | "
        f"AC=[{ac0:.4f},{ac1:.4f}]"
    )
