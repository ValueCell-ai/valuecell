# 使用注意事项

## 环境配置

### 必填 API Key

启动前必须在 `.env` 文件中配置以下关键参数，否则 Agent 无法正常工作：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `OPENROUTER_API_KEY` | 主要 LLM 提供商（覆盖大部分 Agent） | https://openrouter.ai |
| `SEC_EMAIL` | SEC EDGAR API 要求的邮箱标识 | 任意有效邮箱 |

### 可选 API Key

| 变量 | 说明 | 相关 Agent |
|------|------|-----------|
| `GOOGLE_API_KEY` | 使用 Google 原生 API（非 OpenRouter 路由） | Planner / ResearchAgent |
| `OPENAI_API_KEY` | OpenAI 原生接口 | TradingAgents（第三方） |
| `FINNHUB_API_KEY` | 金融新闻与内幕交易数据 | TradingAgents（第三方） |
| `EMBEDDER_API_KEY` / `EMBEDDER_BASE_URL` | 自定义 Embedding 接口（OpenRouter 不支持 Embedding） | ResearchAgent 知识库 |

> **注意**：如使用 OpenRouter 且需要 ResearchAgent 的向量知识库功能，必须单独配置 Embedding 参数，因为 OpenRouter 不提供 Embedding 模型。

---

## 模型 ID 配置

`.env` 中各 Agent 对应的模型 ID 变量：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `PLANNER_MODEL_ID` | `google/gemini-2.5-flash` | 任务规划 + SuperAgent |
| `RESEARCH_AGENT_MODEL_ID` | `google/gemini-2.5-flash` | 研究 Agent |
| `SEC_PARSER_MODEL_ID` | `openai/gpt-4o-mini` | SEC 文件解析 |
| `SEC_ANALYSIS_MODEL_ID` | `deepseek/deepseek-chat-v3-0324` | SEC 分析 |
| `AI_HEDGE_FUND_PARSER_MODEL_ID` | `google/gemini-2.5-flash` | AI 对冲基金解析 |
| `PRODUCT_MODEL_ID` | `anthropic/claude-haiku-4.5` | 资产搜索 Fallback |

> 模型 ID 遵循 OpenRouter 格式：`provider/model-name`，可在 [openrouter.ai/models](https://openrouter.ai/models) 查找。

---

## Agent Card 配置

每个 Remote Agent 通过 `python/configs/agent_cards/*.json` 定义：

```json
{
  "name": "BenGrahamAgent",
  "url": "http://localhost:10011/",
  "enabled": false,
  "skills": [...]
}
```

- **`enabled: false`** 的 Agent 不会被 Planner 发现，也不会被连接。启用时将 `enabled` 改为 `true`
- **`url`** 必须与 Agent 实际监听的地址一致
- Agent Card 文件修改后需要重启服务端才能生效

---

## AI Hedge Fund Agent 特殊限制

`python/third_party/ai-hedge-fund/` 目录下的投资大师 Agent（BenGraham/Buffett 等）目前**仅支持以下股票代码**：

```
AAPL, GOOGL, MSFT, NVDA, TSLA
```

输入其他股票代码会被 Agent 拒绝。这是上游项目的数据限制，未来版本将扩展支持范围。

---

## 自动交易 Agent 注意事项

- **模拟盘优先**：`AutoTradingAgent` 默认使用 Paper Trading（模拟交易）模式，不会产生真实下单
- **真实交易需配置**：使用 Binance 真实账户需要在请求中明确指定 exchange 类型及 API Key
- **加密货币专属**：当前 AutoTradingAgent 仅支持加密货币市场（Binance），不支持股票市场

---

## 数据库

- 默认 SQLite 数据库路径：项目根目录 `valuecell.db`
- 可通过 `VALUECELL_SQLITE_DB` 环境变量覆盖路径（SQLAlchemy URL 格式）
- 数据库在首次启动时自动创建表结构（`init_db.py`）
- 对话历史持久化到 SQLite，重启服务后历史保留

---

## 行情数据

### YFinance（默认）
- 免费，无需 API Key
- 覆盖：美股、港股、加密货币
- 中国大陆网络环境可能访问不稳定，可配置 `XUEQIU_TOKEN` 作为备用

### AKShare（中国市场）
- 免费，无需 API Key
- 覆盖：A 股（沪深北）、港股
- 数据延迟约 15 分钟

### 搜索 Fallback
- 当两个适配器均无结果时，触发 LLM-based 搜索兜底（使用 `PRODUCT_MODEL_ID`）
- 该过程会消耗 LLM Token，高频搜索建议留意用量

---

## 端口使用

| 服务 | 默认端口 | 配置变量 |
|------|----------|----------|
| 前端开发服务器 | 1420 | Vite 配置 |
| 后端 API 服务 | 8000 | `API_PORT` |
| ResearchAgent | 10014 | Agent Card JSON |
| AutoTradingAgent | 10013 | Agent Card JSON |
| AI Hedge Fund Agents | 10011~10020 | Agent Card JSON |

确保以上端口未被其他进程占用。

---

## CORS

后端默认允许所有来源（`CORS_ORIGINS=*`）。生产部署时应修改 `CORS_ORIGINS` 为具体域名：

```env
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
```

---

## 日志

- 后端运行日志输出到 `logs/{timestamp}/*.log`
- Agent 调试模式：设置 `AGENT_DEBUG_MODE=true` 可在控制台看到 Agno Agent 的详细推理过程
- API 接口调试文档：设置 `API_DEBUG=true` 后访问 `http://localhost:8000/docs`（Swagger UI）

---

## 并发注意

- 同一 `conversation_id` 的请求在 Orchestrator 中是串行处理的（通过 asyncio.Lock 保护）
- 不同对话是并发处理的，无相互影响
- 执行上下文（`ExecutionContext`）TTL 为 1 小时（`DEFAULT_CONTEXT_TIMEOUT_SECONDS=3600`），超时后 HITL 状态会被清除

---

## 前端本地开发

```bash
cd frontend
bun install
bun run dev        # 启动 Vite 开发服务器（端口 1420）
```

前端通过 Vite proxy 将 `/api` 请求转发到后端 `http://localhost:8000`，因此需要先启动后端服务。
