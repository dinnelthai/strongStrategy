"""
强势盘策略 (Strong Strategy)
=============================

从 LogEarn 苏醒信号池中筛选强势币，
通过 AO/AC/VWAP 指标判断入场时机。

目录结构:
  strategies/     核心策略逻辑
  indicators/     技术指标（AO, AC, VWAP）
  data/          LogEarn API 客户端
  monitor/       信号轮询池管理
"""
