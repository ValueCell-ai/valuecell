# ValueCell 整体架构

## 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend（前端）                       │
│  React 19 + React Router v7 + Zustand + TailwindCSS      │
│  页面: Home / Market / Agent Chat / Setting              │
└────────────────────┬───────────────────────┬────────────┘
                     │ REST API               │ SSE 流
                     ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend Server（后端服务）                │
│  FastAPI + Uvicorn（端口 8000）                           │
│  Routers: /api/v1/{agents, watchlist, conversation, ...} │
│  Services: AgentStreamService / ConversationService       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Core 调度层（python/valuecell/core/）        │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐  ┌─────────────┐   │
│  │ SuperAgent   │──▶│   Planner    │──▶│ Orchestrator│   │
│  │ (意图分流)    │   │  (任务规划)   │  │  (生命周期) │   │
│  └──────────────┘   └──────────────┘  └──────┬──────┘   │
│                                              │           │
│  ┌───────────────────────────────────────────▼─────────┐ │
│  │            ResponseBuffer + ResponseRouter           │ │
│  │        (流式缓冲 + 持久化 + UI 推送)                 │ │
│  └──────────────────────────────────────────────────── ┘ │
└────────────────────────────────────────────────────────┬─┘
                                                          │ A2A Protocol
                     ┌────────────────────────────────────▼───────────┐
                     │            Remote Agent 层（分布式 Agent）       │
                     │  ┌─────────────┐  ┌──────────────────────────┐  │
                     │  │ Research    │  │ AI Hedge Fund            │  │
                     │  │ Agent       │  │ (BenGraham/Buffett/...)  │  │
                     │  └─────────────┘  └──────────────────────────┘  │
                     │  ┌─────────────┐  ┌──────────────────────────┐  │
                     │  │ AutoTrading │  │ 更多 Agent...             │  │
                     │  │ Agent       │  │                          │  │
                     │  └─────────────┘  └──────────────────────────┘  │
                     └─────────────────────────────────────────────────┘
                                                          │
                     ┌────────────────────────────────────▼───────────┐
                     │          数据层                                  │
                     │  SQLite（对话历史）  YFinance / AKShare（行情）   │
                     └────────────────────────────────────────────────┘
```

---

## 各层职责

### 1. 前端层（`frontend/src/`）

| 模块 | 职责 |
|------|------|
| `app/home/` | 行情列表、观察列表（Watchlist）、股票详情 |
| `app/market/` | Agent 市场，展示可用的所有 Agent 卡片 |
| `app/agent/` | Agent 对话页面，聊天 + 流式渲染 |
| `app/setting/` | 用户设置（Memory 管理等） |
| `store/agent-store.ts` | Zustand 全局状态，管理对话数据树 |
| `lib/sse-client.ts` | Fetch-based SSE 客户端，接收后端流式事件 |
| `components/valuecell/renderer/` | 各类消息渲染器（Markdown/Report/ToolCall/...） |

### 2. 后端服务层（`python/valuecell/server/`）

| 模块 | 职责 |
|------|------|
| `api/app.py` | FastAPI 应用工厂，注册中间件、路由、异常处理器 |
| `api/routers/agent_stream.py` | SSE 流式接口 `POST /api/v1/agents/stream` |
| `api/routers/conversation.py` | 对话历史 CRUD |
| `api/routers/watchlist.py` | 观察列表管理 |
| `api/routers/user_profile.py` | 用户 Profile（语言/时区/Memory） |
| `services/agent_stream_service.py` | 调用 Core 层 Orchestrator 产生流式响应 |
| `db/` | SQLAlchemy ORM + SQLite，持久化 Agent/Asset/Watchlist |

### 3. 核心调度层（`python/valuecell/core/`）

| 模块 | 职责 |
|------|------|
| `coordinate/super_agent.py` | 前置意图分析，决定直接回答 or 转交 Planner |
| `coordinate/planner.py` | 基于 Agno Agent + LLM 将用户意图拆解为 Task 列表 |
| `coordinate/orchestrator.py` | 整体生命周期管理：HITL、Task 执行、流式响应、持久化 |
| `coordinate/response_buffer.py` | 流式 chunk 聚合，为稳定 item_id 做段落级缓冲 |
| `coordinate/response_router.py` | 状态事件路由，触发持久化副作用 |
| `agent/connect.py` | Remote Agent 连接管理（A2A 协议） |
| `conversation/` | 对话元数据 + 消息条目存储（内存/SQLite 双后端） |
| `task/` | Task 状态机（pending→running→completed/failed） |

### 4. Remote Agent 层（各 Agent 进程）

每个 Agent 作为独立的 HTTP 服务运行，通过 A2A 协议与 Core 层通信：

| Agent | 端口 | 说明 |
|-------|------|------|
| ResearchAgent | 10014 | SEC 文件 + Web 搜索 + 知识库 |
| AutoTradingAgent | 10013 | 加密货币自动交易（Binance/模拟盘） |
| AI Hedge Fund Agents | 10011~10020 | 多种投资大师风格（BenGraham/Buffett/...） |
| InvestmentResearchAgent | 可配置 | 综合投研报告 |

### 5. 数据层

| 数据源 | 说明 |
|--------|------|
| SQLite（`valuecell.db`） | 对话历史、消息条目、Watchlist、用户 Profile |
| YFinance | 美股、港股、加密货币实时/历史行情 |
| AKShare | A 股（沪/深/北）、港股行情 |
| OpenRouter / OpenAI / Anthropic | LLM 推理调用 |
| SEC EDGAR | 美股上市公司定期/事件型报告（10-K / 8-K 等） |

---

## 完整请求数据流

### 用户发送一条消息（以 Agent 对话为例）

```
用户在前端输入消息
    │
    ▼
前端 SSEClient.connect(body)
    │  POST /api/v1/agents/stream
    │  { query, agent_name, conversation_id }
    ▼
AgentStreamRouter（FastAPI SSE）
    │  StreamingResponse
    ▼
AgentStreamService.stream_query_agent()
    │
    ▼
AgentOrchestrator.process_user_input()
    │
    ├─── [无 target_agent_name] SuperAgent.run()
    │         判断: ANSWER / HANDOFF_TO_PLANNER
    │
    ├─── [转交 Planner] ExecutionPlanner.create_plan()
    │         Agno Agent (LLM) → PlannerResponse → Task 列表
    │         [可能] HITL: UserInputRequest → plan_require_user_input 事件
    │
    └─── 执行 Task 列表（串行）
              │
              ▼
         RemoteConnections.start_agent() → A2A Client
              │
              ▼
         远端 Agent 处理（流式输出）
              │
              ▼
         TaskStatusUpdateEvent → ResponseBuffer.annotate()
              │
              ▼
         持久化 SaveItem → SQLite
              │
              ▼
         SSE chunk → 前端
    │
    ▼
前端 SSEClient.onData(SSEData)
    ▼
useAgentStore.dispatchAgentStore(action)
    ▼
updateAgentConversationsStore() 更新状态树
    ▼
React 重新渲染对话区域
```

---

## 配置文件与启动脚本

| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量模板，含 API Key、模型 ID、端口等 |
| `start.sh / start.ps1` | 一键启动前端 + 后端 + 所有 Agent |
| `python/configs/agent_cards/*.json` | Agent 描述卡片，定义 Agent URL / 技能 / 元数据 |
| `frontend/vite.config.ts` | Vite 构建配置，前端开发服务端口 1420 |
| `python/valuecell/server/config/settings.py` | 后端配置（从环境变量读取） |
