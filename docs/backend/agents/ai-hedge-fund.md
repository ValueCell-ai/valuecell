# AI Hedge Fund Agents（AI 对冲基金）

路径：`python/valuecell/third_party/ai-hedge-fund/`

AI Hedge Fund 是对 [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) 的集成，包含多个模拟顶级投资大师风格的 AI Agent，各自采用不同的分析方法论对股票进行评估。

---

## 投资大师 Agent 列表

| Agent | 投资风格 | 核心方法论 |
|-------|----------|-----------|
| `BenGrahamAgent` | 价值投资 | 安全边际、格雷厄姆数、清算价值 |
| `WarrenBuffettAgent` | 价值+成长投资 | 护城河、ROIC、长期持有 |
| `CharlieMungerAgent` | 价值投资（心智模型） | 心智模型、逆向思维、商业质量 |
| `PeterLynchAgent` | 成长投资 | PEG 比率、行业专精、GARP |
| `PhilFisherAgent` | 成长投资 | 定性分析、管理层质量、scuttlebutt |
| `BillAckmanAgent` | 激进投资者 | 集中持仓、催化剂识别、管理层变革 |
| `CathieWoodAgent` | 颠覆性创新 | 指数级成长、科技颠覆、五年视野 |
| `MichaelBurryAgent` | 深度价值/逆向 | 深度基本面研究、极端逆向操作 |
| `StanleyDruckenmillerAgent` | 宏观投资 | 宏观经济判断、流动性分析、押注尾部事件 |
| `MohnishPabraiAgent` | Dhandho 投资 | 低风险高收益、复制成功范式 |
| `AswathDamodaranAgent` | 估值 | DCF、相对估值、价值驱动因子 |
| `RakeshJhunjhunwalaAgent` | 印度市场价值 | 印度股市、长期持有 |
| `FundamentalsAnalystAgent` | 基本面 | 综合财务指标分析 |
| `PortfolioManagerAgent` | 投资组合 | 多 Agent 协作，最终投资决策 |
| `RiskManagerAgent` | 风险管理 | 风险评估、仓位管理 |
| `TechnicalAnalystAgent` | 技术分析 | 图表形态、指标分析 |
| `ValuationAgent` | 估值 | 多维估值方法 |

---

## 重要限制

> **当前仅支持以下 5 只美股股票代码**：
> `AAPL`, `GOOGL`, `MSFT`, `NVDA`, `TSLA`

这是上游数据源（`yfinance` + `finnhub`）的限制，未来版本将扩展支持范围。对其他股票代码的查询会被 Agent 拒绝。

---

## Agent 协作架构

这些 Agent 使用 LangGraph 构建多 Agent 协作工作流：

```
用户输入（股票代码 + 时间范围）
    │
    ├── 并行分析阶段
    │   ├── FundamentalsAnalystAgent  → 财务指标分析
    │   ├── TechnicalAnalystAgent     → 技术指标分析
    │   ├── ValuationAgent            → 估值分析
    │   └── [投资大师 Agents]         → 各自风格分析
    │
    └── 决策阶段
        ├── RiskManagerAgent         → 风险评估 → 仓位建议
        └── PortfolioManagerAgent    → 综合所有分析 → 最终交易决策
```

---

## Agent Card 配置

每个 Agent 在 ValueCell 中有对应的 Card 文件（默认 `enabled: false`，需手动启用）：

```
python/configs/agent_cards/
├── ben_graham_agent.json           (端口 10011)
├── warren_buffett_agent.json       (端口 10012, 示例)
├── investment_research_agent.json  (综合投研)
└── ...
```

启用方法：将对应 JSON 文件中的 `"enabled": false` 改为 `"enabled": true`，然后重启服务。

---

## 数据来源

| 数据类型 | 来源 | 需要 Key |
|----------|------|----------|
| 财务数据 | Yahoo Finance | 否 |
| 新闻/情绪 | Finnhub | 是（`FINNHUB_API_KEY`） |
| 内幕交易 | Finnhub | 是 |
| Web 搜索 | OpenAI Browsing / Tavily | 是（`OPENAI_API_KEY`） |

---

## 独立运行

AI Hedge Fund 可以脱离 ValueCell UI 独立运行（命令行模式），详见上游项目文档：

```bash
cd python/third_party/ai-hedge-fund
uv run python src/main.py --ticker AAPL --show-reasoning
```

---

## 启动说明

作为 ValueCell 的 Remote Agent 启动：

```bash
cd python/third_party/ai-hedge-fund
bash launch_adapter.sh
```

`launch_adapter.sh` 会启动 A2A 兼容的 HTTP 服务，使 ValueCell Core 层可以通过 A2A 协议与之通信。

---

## 配置要求

| 变量 | 说明 |
|------|------|
| `AI_HEDGE_FUND_PARSER_MODEL_ID` | 请求解析模型（默认 `google/gemini-2.5-flash`） |
| `OPENAI_API_KEY` | 财务数据搜索 |
| `FINNHUB_API_KEY` | 新闻与内幕交易数据 |
| `OPENROUTER_API_KEY` | Agent LLM 推理（主要提供商） |
