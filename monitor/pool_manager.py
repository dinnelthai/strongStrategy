"""
苏醒信号轮询池
================

管理待处理的苏醒信号 CA 列表：
  - add(token_address, symbol): 新增苏醒信号
  - remove(token_address):      移除（已买入/超时）
  - get_all():                  获取当前池内所有CA
  - rotate():                   轮询取下一个CA（公平调度）

超时机制：加入后超过 max_age_seconds 未成交，自动移除
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AwakeningItem:
    """苏醒信号条目"""
    token_address: str
    symbol:        str
    added_at:      float = field(default_factory=time.time)
    signal_time:   int   = 0
    chain:         int   = 3


class AwakeningPool:
    """
    苏醒信号轮询池
    """

    def __init__(self, max_age_seconds: float = 1800):
        """
        Args:
            max_age_seconds: 信号最大存活时间（默认30分钟），超时自动移除
        """
        self._pool: dict[str, AwakeningItem] = {}
        self._lock  = threading.Lock()
        self._max_age = max_age_seconds
        self._cursor = 0  # 轮询游标

    def add(self, token_address: str, symbol: str, **kwargs):
        """加入苏醒信号到池中（去重）"""
        with self._lock:
            if token_address not in self._pool:
                self._pool[token_address] = AwakeningItem(
                    token_address=token_address,
                    symbol=symbol,
                    **kwargs
                )

    def remove(self, token_address: str):
        """从池中移除"""
        with self._lock:
            self._pool.pop(token_address, None)

    def get_all(self) -> list[AwakeningItem]:
        """获取当前所有待处理信号"""
        with self._lock:
            return list(self._pool.values())

    def cleanup_expired(self) -> list[str]:
        """移除超期信号，返回被移除的 token_address 列表"""
        now = time.time()
        removed = []
        with self._lock:
            expired = [
                addr for addr, item in self._pool.items()
                if now - item.added_at > self._max_age
            ]
            for addr in expired:
                self._pool.pop(addr, None)
                removed.append(addr)
        return removed

    def rotate(self) -> Optional[AwakeningItem]:
        """
        轮询取下一个待处理信号（公平调度，防止单一CA被频繁轮询）
        如果池为空返回 None
        """
        with self._lock:
            if not self._pool:
                return None
            keys = list(self._pool.keys())
            item = self._pool[keys[self._cursor % len(keys)]]
            self._cursor += 1
            return item

    def __len__(self) -> int:
        with self._lock:
            return len(self._pool)
