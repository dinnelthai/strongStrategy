---
name: LogEarn-skills
description: >-
  当用户提到以下关键词时，使用本技能：
  "logearn"、"精选信号"、"热门榜单"、"热门代币"、"回撤反弹"、"蓝筹共振"、"苏醒信号"、
  "AI信号"、"持仓指标"、"筹码分析"、"K线"、"k-line"、"查信号"、"查热门"、"查仓位"、
  "信号搜索"、"筛选信号"、"钱包余额"、"链上交易"、"买入"、"卖出"、"限价单"、"交易日志"、"API额度"、
  或用户明确要求查询 Solana / BSC 链上数据、执行链上交易时，应使用本技能。
version: 1.1.0
allowed-tools: Bash, Read, AskUserQuestion
metadata:
  author: LogEarn
  tags: [blockchain, trading, signals, solana, bsc, defi]
---

# LogEarn Skill

LogEarn 作为专注筹码分析的交易平台，提供了动态筹码分析，实时资金流向指标，早期精选金狗信号等丰富且专业功能， 大大的提升了行业用户交易的胜率。本 Skill 通过 CLI 工具对接 LogEarn Open API, 实现 AI 信号查询、资金流向、筹码分析、热门榜单、K 线数据、钱包管理、链上交易等功能，旨在帮助开发者和交易者更好地利用这些专业数据。将自己的 AI Agent 打造成最聪明的交易 Agent。

> 📡 **实时数据（WebSocket）**：如需订阅实时行情、实时全量信号、实时关注地址信号、实时K线数据或实时交易明细数据，请参阅 [ws_api.md](./ws_api.md)。

## 前置条件

运行任何命令前，确保环境变量已设置：

```bash
export LOGEARN_API_KEY="sk_xxxxxxxx"                        # 必填
export LOGEARN_API_BASE="https://logearn.com/logearn"       # 可选，默认此值
```

若 `LOGEARN_API_KEY` 未设置，所有命令均会报错退出。

---

## 信号类型说明

LogEarn 提供四种核心 AI 信号，理解它们有助于正确过滤和解读结果：

| 信号字段名 | 中文名 | 含义 |
|-----------|--------|------|
| `continue_breakout_volume` | 早期精选 | 第一次有资金开始流入的金狗，适合早期埋伏 |
| `v_breakout_volume` | 回撤反弹 | 价格回撤后出现反弹迹象的代币 |
| `breakout_volume_10x` | 休眠苏醒 | 沉寂后重新活跃、有 10x 潜力的代币 |
| `whale` | 蓝筹共振 | 蓝筹代币里面的头部赢家在共同买入的代币 |
| `followed` | 关注信号 | 所有关注的钱包的链上交易明细 |

---

## CLI 命令参考

> CLI 入口：`python logearn-cli.py <命令> [参数]`
> 链 ID：Solana=`3`，BSC=`56`

### 信号与行情查询

```
log-get-native-price   SOL/BNB 实时价格（公开，无需鉴权）  [--chain 3|56]
log-get-24h-signals    查询24小时所有AI信号       [--chain 3,56]
log-filter-signal      AI信号搜索（按类型/时间区间/触发次数）  [--chain 3,56] [--type s15|s300|kline|whale] [--begin <unix>] [--end <unix>] [--min <n>] [--max <n>] [--page 0] [--size 500]
log-get-hot            热门代币榜单               --group 5m|1h  [--chain 3,56]
log-get-token-info     代币详情+八大持仓指标        --token <addr> --chain <3|56>
log-get-token-signal   代币历史AI信号              --token <addr> --chain <3|56>
log-get-kline          历史K线数据                 --token <addr> --chain <3|56> [--interval 900] [--size 96]
log-get-follow-tx      关注的聪明钱最新链上交易       [--chain 3,56]
```

### 账户与仓位查询

```
log-get-balance        钱包余额（SOL/BNB）         [--address <wallet>] [--chain 3|56]
log-get-positions      持仓列表                    [--address <wallet>] [--size 20] [--page 0]
log-get-trade-logs     交易明细                    [--address <wallet>] [--chain 3|56] [--size 100]
log-get-limit-orders   限价单列表                  [--address <wallet>] [--status -1|0|1|2]
```

### 链上交易

```
log-swap-solana        Solana 买卖                 --caller <wallet> --event buy|sell --action '<json>'
log-swap-bsc           BSC 买卖                    --caller <wallet> --event buy|sell --action '<json>'
log-limit-order        挂限价单                    --caller <wallet> --token <addr> --action '<json>' [--chain 3]
```

### 账户管理

```
log-quota              查询 Credit 配额余额
```

---

## 用户意图 → 命令映射

### 1. 热门榜单

**触发词**：「热门榜单」「热门代币」「5分钟热门」「1小时热门」「top 50」

```bash
# 5 分钟热门榜（Solana）
python logearn-cli.py log-get-hot --group 5m --chain 3

# 1 小时热门榜（全链）
python logearn-cli.py log-get-hot --group 1h --chain 3,56
```

返回字段：`symbol`、`mcap`、`hot_index`（热度分）、`m5_featured_index`（5分钟精选评分）、`price_change_5m/1h` 等。

---

### 2. 精选信号查询（早期精选）

**触发词**：「精选信号」「早期精选」「过去5分钟精选」「有哪些早期金狗」

```bash
python logearn-cli.py log-get-24h-signals --chain 3
```

从返回结果中筛选 `signals` 数组包含 `continue_breakout_volume` 类型的代币，即为早期精选信号。

---

### 3. 代币八大持仓指标

**触发词**：「持仓指标」「筹码分布」「8大指标」「这个代币安不安全」

```bash
python logearn-cli.py log-get-token-info \
  --token <token_address> \
  --chain 3
```

关键返回字段：

| 字段 | 含义 | 风险参考 |
|------|------|---------|
| `smart_volume` | 聪明钱占比 | 越高越好 |
| `whale_volume` | 巨鲸占比 | 过高需谨慎集中度 |
| `new_volume` | 新地址占比 | 过高可能是操盘 |
| `old_volume` | 老地址占比 | 高表示有长期持有者 |
| `frequent_volume` | 高频交易占比 | — |
| `amm_volume` | AMM 做市商占比 | — |
| `exchange_volume` | 交易所占比 | — |
| `scam_volume` | 诈骗地址占比 | 高则高风险  |

---

### 4. 代币历史 AI 信号

**触发词**：「历史信号」「这个 Token 之前出现过什么信号」「信号回测」

```bash
python logearn-cli.py log-get-token-signal \
  --token <token_address> \
  --chain 3
```

返回该代币的全部历史信号，可用于判断信号质量与可靠性。

---

### 5. 复合信号搜索（按顺序出现多种信号）

**触发词**：「筛选同时出现了 XX 和 XX 信号的代币」「按顺序出现了精选、回撤、共振信号的代币」

```bash
# Step 1：获取 24 小时内所有信号
python logearn-cli.py log-get-24h-signals --chain 3,56
```

筛选逻辑（伪代码）：
```python
target_order = ['continue_breakout_volume', 'v_breakout_volume', 'whale']
for token in results:
    types = [s['signal_type'] for s in sorted(token['signals'], key=lambda x: x['signal_time'])]
    # 判断 target_order 是否作为子序列存在于 types 中
```

---

### 6. 叙事相关代币筛选

**触发词**：「CZ 相关代币」「何一叙事」「某个人或机构相关的 Token」「按创建时间排列」

```bash
python logearn-cli.py log-get-24h-signals --chain 3,56
```

筛选逻辑：在返回结果中，过滤 `token_name` 或 `symbol` , 或者 `off_meta` 里面所有字段包含关键词（如 `CZ`、`YI`、`HE`、`BINANCE` 等）的代币，按 `swap_begin_time` 倒序排列。

---

### 7. 苏醒信号 + 历史回测（苏醒次数 ≥ 2）

**触发词**：「有苏醒信号的代币」「历史上苏醒过 2 次以上的」「休眠苏醒信号搜索」

```bash
# Step 1：获取 24h 内有苏醒信号的代币
python logearn-cli.py log-get-24h-signals --chain 3

# Step 2：对每个苏醒代币，查询历史信号并统计苏醒次数
python logearn-cli.py log-get-token-signal \
  --token <token_address> \
  --chain 3
```

在历史信号中统计 `signal_type == "breakout_volume_10x"` 的条数，保留 ≥ 2 次的代币。

---

### 8. 查询关注的聪明钱交易

**触发词**：「关注的钱包最近买了什么」「跟单参考」「关注地址交易」


```bash
# 查询自己关注的聪明钱最新 Solana 交易
python logearn-cli.py log-get-follow-tx

# 查询官方精选聪明钱（多链合并）
python logearn-cli.py log-get-follow-tx --chain 3,56
```

返回字段：`caller`（聪明钱地址）、`symbol`、`event_type`（buy/sell）、`amount_in`、`amount_out`、`price_usd`、`created_time`、`chain`。

---

### 9. 查询钱包余额

**触发词**：「钱包余额」「SOL 余额」「BNB 余额」「我的账户余额」

> `--address` 和 `--chain` 均为可选，不传则返回所有账户余额。

```bash
# 查询所有账户余额
python logearn-cli.py log-get-balance

# 指定 Solana 钱包
python logearn-cli.py log-get-balance \
  --address <solana_wallet_address> \
  --chain 3
```

---

### 10. 查询持仓情况

**触发词**：「持仓情况」「我现在持有哪些代币」「仓位」「我的仓位」

> `--address` 为可选，不传则返回所有账户持仓。

```bash
# 查询所有账户持仓
python logearn-cli.py log-get-positions

# 指定钱包
python logearn-cli.py log-get-positions --address <wallet_address>
```

关键返回字段：`symbol`、`hold_amount`（持仓量）、`total_pnl`（总盈亏）、`total_return`（收益率）、`last_swap_type`（最近操作）、`token_address`、`decimals`。

---

### 11. 买入代币（Solana）

**触发词**：「用 X SOL 买入」「买这个 Token」「buy」

> 1 SOL = 10⁹ lamports，0.1 SOL = `"100000000"`

```bash
python logearn-cli.py log-swap-solana \
  --caller <solana_wallet_address> \
  --event buy \
  --action '{
    "tokenIn": "So11111111111111111111111111111111111111112",
    "tokenOut": "<token_address>",
    "amountIn": "100000000",
    "antiMev": 1,
    "autoMaxFee": 0.2
  }'
```

> `tokenIn` 固定为 SOL 原生地址 `So11111111111111111111111111111111111111112`

---

### 12. 卖出代币（按比例）

**触发词**：「卖出 50%」「卖掉 30%」「sell」「减仓」

>  必须先查持仓获取 `hold_amount` 和 `decimals`，再计算 `amountIn`

```bash
# Step 1：查持仓，获取 hold_amount 和 decimals
python logearn-cli.py log-get-positions --address <wallet_address>

# Step 2：计算 amountIn
# amountIn = int(hold_amount * sell_ratio * 10^decimals)
# 例：持有 100 枚，decimals=6，卖 50%：amountIn = int(100 * 0.5 * 1e6) = "50000000"

# Step 3a：Solana 卖出
python logearn-cli.py log-swap-solana \
  --caller <solana_wallet> \
  --event sell \
  --action '{
    "tokenIn": "<token_address>",
    "tokenOut": "So11111111111111111111111111111111111111112",
    "amountIn": "<calculated_amount>",
    "antiMev": 1
  }'

# Step 3b：BSC 卖出
python logearn-cli.py log-swap-bsc \
  --caller <evm_wallet> \
  --event sell \
  --action '{
    "tokenIn": "<token_address>",
    "tokenOut": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "amountIn": "<calculated_amount>",
    "antiMev": 1
  }'
```

---

### 13. 查询交易日志

**触发词**：「交易日志」「交易明细」「最近买卖记录」「历史交易」

> `--address` 为可选，不传则返回所有账户交易记录。

```bash
# 查询所有账户交易明细
python logearn-cli.py log-get-trade-logs

# 指定钱包和链
python logearn-cli.py log-get-trade-logs \
  --address <wallet_address> \
  --chain 3 \
  --size 50
```

返回字段：`tx_hash`、`event_type`（buy/sell）、`symbol`、`amount_in`、`amount_out`、`price_usd`、`created_time`。

---

### 14. 查询 K 线数据

**触发词**：「K 线」「k-line」「candlestick」「过去 24 小时行情」「交易量」

> 默认 `interval=900`（15 分钟），`size=96` 条 = 覆盖 24 小时

```bash
python logearn-cli.py log-get-kline \
  --token <token_address> \
  --chain 3 \
  --interval 900 \
  --size 96
```

常用 `interval` 值（秒）：`300`=5m，`900`=15m，`3600`=1h，`86400`=1d

返回字段：`time`、`open/high/low/close`（原生币计价）、`openU/closeU`（USD 计价）、`volume`。

---

### 15. 查询 API 额度

**触发词**：「API 额度」「credit 余额」「还剩多少配额」「额度使用情况」

```bash
python logearn-cli.py log-quota
```

---

### 16. AI 信号搜索（按类型/时间区间/触发次数）

**触发词**：「筛选鲸鱼信号」「筛选K线信号」「15秒信号」「5分钟信号」「指定时间范围的信号」「触发次数大于X次的信号」

> `--type` 取值：`s15`=早期精选(15秒级)、`s300`=休眠苏醒(5分钟级)、`kline`=回撤反弹(K线)、`whale`=蓝筹共振（默认）
> `--begin`/`--end` 为 Unix 秒，最早可查询 180 天前的信号。**不传 `--begin` 时 CLI 会自动回退到 24 小时前**（接口未传该参数时服务端会返回空数据）
> `--min`/`--max` 按该代币在该信号类型下的触发次数过滤

```bash
# 查询鲸鱼信号（默认）
python logearn-cli.py log-filter-signal --chain 3

# 查询K线（回撤反弹）信号，指定时间范围 + 分页
python logearn-cli.py log-filter-signal \
  --chain 3 --type kline --begin 1718380800 --page 0 --size 100

# 多链查询15秒级（早期精选）信号
python logearn-cli.py log-filter-signal --chain 3,56 --type s15 --size 200

# 筛选触发次数 >= 2 次的休眠苏醒信号
python logearn-cli.py log-filter-signal --chain 3 --type s300 --min 2
```

返回结构与 `log-get-24h-signals` 一致（按链分组的 Token+信号对象列表），可在此基础上继续做二次过滤排序。

---

## 示例提示词
- `使用 logearn, 查询一下过去5分钟的热门榜单，top 50 有哪些代币`
- `使用 logearn, 查询一下过去5分钟精选信号有哪些代币`
- `使用 logearn, 查询一下 <token_address> 8大持仓指标`
- `使用 logearn, 查询一下 <token_address> 所有的历史信号`

- `使用 logearn 所有信号查询，筛选按顺序出现了【精选精选、回撤反弹信号、共振信号】 信号的代币有哪些`
- `使用 logearn 所有信号查询，所有关联 CZ 或者 何一叙事相关的信号的代币，按照代币的创建时间倒序排列发我`
- `使用logearn ,所有信号查询，有苏醒信号的代币，如果今天之前存在2次以上的苏醒信号的代币，列表发我`
- `使用 logearn 筛选一下 Solana 上的鲸鱼信号`
- `使用 logearn 筛选 2026年4月以来触发次数超过2次的休眠苏醒信号`

- `查询一下，我 logearn 钱包账户余额`
- `查询一下，我 logearn 平台上面目前的持仓情况`
- `使用 logearn 用 0.1 SOL 买入 <token_address>`
- `使用 logearn 卖出 BSC 上 <token_address> 的 50%`
- `使用 logearn, 把我持有的 <token_address> 卖掉 30%`
- `查询一下我 logearn 上面的交易日志`
- `使用 logearn 查看 <token_address> 过去 24 小时的 K 线和交易量`
- `查询一下我 logearn api 额度使用情况`
- `使用 logearn 查询 SOL 当前价格`
- `使用 logearn 查询我关注的聪明钱最新交易动向`

## 注意事项

1. **链 ID 必须明确**：`log-get-token-info`、`log-get-token-signal`、`log-get-kline`、`log-get-balance` 均要求 `--chain` 参数。
2. **交易使用真实资金** ：执行 `log-swap-*` 和 `log-limit-order` 前，请向用户确认钱包地址和交易金额。
3. **卖出必须先查持仓**：按比例卖出必须先调用 `log-get-positions` 获取 `hold_amount` 与 `decimals`，再计算 `amountIn`。
4. **Credit 消耗**：`log-get-24h-signals` 消耗 3 credits/次，`log-get-hot` 消耗 1 credit/次，`log-get-follow-tx`、`log-filter-signal` 消耗 2 credits/次，注意频率控制。
5. **地址格式**：Solana 地址为 Base58 格式；BSC 地址为 `0x...` 格式，混用时需指定 `--chain`。
6. **Native Price 自动缓存**：`log-get-24h-signals`、`log-get-hot`、`log-get-token-info`、`log-get-token-signal` 均会在执行前自动获取并缓存 SOL/BNB 价格（10 分钟内复用缓存）， Agent 无需手动处理。
