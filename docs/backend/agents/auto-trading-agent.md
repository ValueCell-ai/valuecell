# Auto Trading Agent（自动交易 Agent）

路径：`python/valuecell/agents/auto_trading_agent/`
端口：`10013`（默认）

Auto Trading Agent 是一个加密货币自动交易系统，集成技术分析、AI 信号生成、仓位管理和交易执行功能，支持 Binance 真实交易和模拟盘（Paper Trading）。

---

## 核心功能

| 功能模块 | 文件 | 说明 |
|----------|------|------|
| 主 Agent 逻辑 | `agent.py` | 多实例管理、流式输出、通知推送 |
| 技术分析 | `technical_analysis.py` | RSI、MACD、布林带等指标 + AI 信号生成 |
| 投资组合决策 | `portfolio_decision_manager.py` | 综合多个资产分析决策 |
| 仓位管理 | `position_manager.py` | 持仓跟踪、盈亏计算 |
| 交易执行 | `trading_executor.py` | 下单、撤单、仓位平仓 |
| 市场数据 | `market_data.py` | 实时/历史行情获取 |
| 交易所适配 | `exchanges/` | Binance / Paper Trading 适配器 |
| 交易记录 | `trade_recorder.py` | 交易历史记录与统计 |
| 格式化输出 | `formatters.py` | 消息格式化（发送到前端） |

---

## 交易所支持

| 交易所 | 文件 | 说明 |
|--------|------|------|
| Binance | `exchanges/binance_exchange.py` | 真实加密货币交易 |
| Paper Trading | `exchanges/paper_trading.py` | 模拟盘，不产生真实订单 |
| Base | `exchanges/base_exchange.py` | 抽象基类 |

---

## 多实例架构

Auto Trading Agent 支持在同一 Agent 实例中运行多个独立的交易实例（每个用于不同的资产/策略）：

```python
# 多实例状态结构
# {session_id: {instance_id: TradingInstanceData}}
self._trading_instances: Dict[str, Dict[str, TradingInstanceData]] = {}
```

每个实例拥有独立的：
- 配置（资产、交易对、初始资金）
- 仓位状态
- 交易历史

---

## 技术分析指标

`TechnicalAnalyzer` 计算以下指标：

| 指标 | 说明 |
|------|------|
| RSI | 相对强弱指数（超买/超卖） |
| MACD | 移动平均收敛散度（趋势跟踪） |
| 布林带 | 价格波动区间 |
| EMA | 指数移动平均 |
| 成交量分析 | 量价关系 |

`AISignalGenerator` 使用 LLM 综合技术指标，输出交易信号（买入/卖出/持有）。

---

## 流程说明

### stream()（用户触发）

用户通过聊天界面配置并启动交易实例：

```
用户输入：帮我对 BTC 进行自动交易，初始资金 1000 USDT，使用保守策略

AutoTradingAgent.stream()
    │  LLM 解析 TradingRequest（资产、金额、策略）
    ▼
创建 TradingInstanceData
    │  初始化 TechnicalAnalyzer + TradingExecutor
    ▼
开始交易循环（每 X 分钟检查一次）
    │  获取市场数据 → 技术分析 → AI 信号 → 执行决策
    ▼
流式输出交易状态更新（FilteredLineChartComponentData / FilteredCardPushNotificationComponentData）
```

### notify()（Agent 主动推送）

当 `TaskPattern.RECURRING` 时，Agent 定期运行分析并主动推送通知到前端（无需用户触发）。

---

## 输出组件类型

| 组件类型 | 说明 |
|----------|------|
| `filtered_line_chart` | 资产价格走势图（可按时间范围过滤） |
| `filtered_card_push_notification` | 交易信号卡片（买入/卖出/持有 + 理由） |

---

## 配置

### 环境变量

| 变量 | 说明 |
|------|------|
| `TRADING_PARSER_MODEL_ID` | 请求解析模型（继承 `DEFAULT_AGENT_MODEL`） |
| `OPENROUTER_API_KEY` | LLM 推理 |

### AutoTradingConfig

```python
class AutoTradingConfig(BaseModel):
    exchange: str           # "binance" / "paper"
    symbol: str             # 如 "BTC/USDT"
    initial_capital: float  # 初始资金
    strategy: str           # "conservative" / "moderate" / "aggressive"
    check_interval: int     # 检查间隔（秒），默认 300（5 分钟）
    api_key: Optional[str]  # Binance API Key（真实交易时需要）
    api_secret: Optional[str]
```

---

## 注意事项

1. **模拟盘优先**：生产环境建议先使用 `paper` 模式验证策略
2. **资金风险**：真实交易存在亏损风险，请谨慎使用
3. **API 限制**：Binance API 有请求频率限制，`check_interval` 不建议设置过小
4. **无法保证盈利**：AI 信号仅供参考，不构成投资建议
