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
# VWAP 条件：收盘价站上 VWAP 即可
AO_LOOKBACK           = 3      # 连续 N 根 AO 需 > 0 且递增


def _num(x) -> float:
    try:
        v = float(x)
        return v if v == v else 0.0  # NaN guard
    except (TypeError, ValueError):
        return 0.0


def check_static_conditions(token_meta: dict) -> tuple[bool, str]:
    """
    入池前静态过滤（不需要 K 线）：条件 1-6。
    返回 (True, "") 表示通过，(False, 原因) 表示淘汰。
    """
    symbol = token_meta.get("symbol", "UNKNOWN")
    now_ts = time.time()

    platform = token_meta.get("platform", "")
    if platform not in ALLOW_PLATFORMS:
        return False, f"平台不在白名单：{platform}"

    launch_ts = _num(token_meta.get("swap_begin_time", 0))
    age_days  = (now_ts - launch_ts) / 86400 if launch_ts > 0 else float("inf")
    if launch_ts <= 0 or age_days > AGE_MAX_DAYS:
        return False, f"年龄不符（{age_days:.1f}天）"

    if not (_num(token_meta.get("launch_time_duration", 0)) > 0):
        return False, "未毕业到外盘"

    m_launch_ts = _num(token_meta.get("launch_time", 0))
    if m_launch_ts > 0:
        after_launch = now_ts - m_launch_ts
        if after_launch < GRADUATION_MIN_SEC:
            return False, f"外盘毕业不足{GRADUATION_MIN_SEC//60}分钟（{after_launch:.0f}秒）"

    if _num(token_meta.get("shit_volume", 0)) >= SHIT_VOLUME_MAX_PCT:
        return False, f"垃圾钱包占比过高：{_num(token_meta.get('shit_volume')):.1f}%"

    if _num(token_meta.get("new_volume", 0)) >= NEW_VOLUME_MAX_PCT:
        return False, f"新钱包占比过高：{_num(token_meta.get('new_volume')):.1f}%"

    buyer_count = _num(token_meta.get("buyer_count_d1", 0))
    if buyer_count <= BUY_TX_MIN_D1:
        return False, f"24h买入地址不足：{buyer_count:.0f}"

    return True, ""


def check_entry_conditions(candles_1m: list, token_meta: dict) -> tuple[bool, str]:
    """
    检查是否满足买入条件。

    Args:
        candles_1m:  按时间升序排列的1分钟K线列表，每条包含 open/high/low/close/volume
        token_meta:  从 LogEarn 取得的代币元数据（platform, swap_begin_time, 等）

    Returns:
        (是否满足, 原因描述)
    """
    # ------------------------------------------------------------------
    # 条件 1-6：复用静态过滤（入池前已过滤，这里二次保障）
    # ------------------------------------------------------------------
    ok, reason = check_static_conditions(token_meta)
    if not ok:
        return False, reason

    now_ts = time.time()
    launch_ts = _num(token_meta.get("swap_begin_time", 0))
    age_days  = (now_ts - launch_ts) / 86400 if launch_ts > 0 else float("inf")

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
    # 7. 收盘价站上 VWAP
    # ------------------------------------------------------------------
    vwap = calc_vwap(closes, highs, lows, volumes)
    last_close = closes[-1]
    if vwap <= 0 or last_close <= vwap:
        return False, f"价格未站上VWAP（收盘:{last_close:.6f} VWAP:{vwap:.6f}）"

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
    # 9. AC：最近 3 根全 > 0 且严格递增（ac0 > ac1 > ac2）
    #    AC(i) = AO[i] - SMA(AO[i-4..i])
    # ------------------------------------------------------------------
    def _ac_at(idx_from_end: int) -> Optional[float]:
        """idx_from_end=0 → 最新，1 → 上一根，2 → 上上根"""
        pos = len(ao_series) - 1 - idx_from_end
        if pos - 4 < 0:
            return None
        window = ao_series[pos - 4 : pos + 1]
        return ao_series[pos] - sum(window) / 5

    ac0 = _ac_at(0)
    ac1 = _ac_at(1)
    ac2 = _ac_at(2)
    if ac0 is None or ac1 is None or ac2 is None:
        return False, "AC数据不足"
    if not (ac0 > 0 and ac1 > 0 and ac2 > 0):
        return False, f"AC未全部>0：[{ac0:.4f},{ac1:.4f},{ac2:.4f}]"
    if not (ac0 > ac1 > ac2):
        return False, f"AC未递增：[{ac0:.4f},{ac1:.4f},{ac2:.4f}]"

    # ------------------------------------------------------------------
    # 全部通过
    # ------------------------------------------------------------------
    return True, (
        f"[命中] {symbol} | "
        f"年龄={age_days:.1f}天 | "
        f"VWAP={vwap:.6f} 收盘={last_close:.6f} | "
        f"AO=[{ao0:.4f},{ao1:.4f},{ao2:.4f}] | "
        f"AC=[{ac0:.4f},{ac1:.4f},{ac2:.4f}]"
    )
