# ValueCell 项目文档

ValueCell 是一个社区驱动的多智能体（Multi-Agent）金融应用平台，集成多个顶级投资风格的 AI Agent，帮助用户进行股票行情查看、投资研究、自动化交易等。

## 目录结构

```
docs/
├── README.md                      # 本文件：项目概述与导航
├── architecture.md                # 整体架构与分层说明
├── concepts.md                    # 核心概念（SSE / A2A / 事件模型等）
├── notes.md                       # 使用注意事项与常见问题
├── backend/
│   ├── core/
│   │   ├── README.md              # 核心调度层（Orchestrator / Planner / SuperAgent）
│   │   ├── agent-connection.md    # Agent 连接管理（Card / Client / Connect / Listener）
│   │   ├── conversation.md        # 对话管理（Manager / Store / ItemStore / 模型）
│   │   └── task.md                # 任务管理（Task / TaskManager）
│   ├── adapters/
│   │   └── README.md              # 资产数据适配器（YFinance / AKShare / Manager）
│   ├── server/
│   │   └── README.md              # HTTP 服务端（Routers / Schemas / Services / DB）
│   └── agents/
│       ├── README.md              # 内置 Agent 概览
│       ├── research-agent.md      # 研究 Agent（SEC 文件 / 知识库 / Web 搜索）
│       ├── auto-trading-agent.md  # 自动交易 Agent（加密货币 / Binance）
│       └── ai-hedge-fund.md       # AI 对冲基金（多投资大师风格分析）
├── frontend/
│   ├── pages/
│   │   └── README.md              # 页面路由与各页功能
│   ├── agent-chat/
│   │   └── README.md              # Agent 对话界面组件
│   └── state/
│       └── README.md              # 状态管理与 SSE 通信客户端
└── examples/
    └── README.md                  # 典型使用场景与示例
```

---

## 项目简介

| 属性 | 说明 |
|------|------|
| 定位 | 多智能体金融分析与交易平台 |
| 协议 | Agent2Agent（A2A）协议驱动的分布式 Agent 网络 |
| 数据流 | 后端 SSE 流式推送，前端实时渲染 |
| 存储 | SQLite 持久化对话与消息历史 |
| LLM | 支持 OpenRouter、OpenAI、Anthropic、Google、Ollama |
| 行情数据 | YFinance（美股/港股）、AKShare（A 股/港股） |
| 前端框架 | React 19 + React Router v7 + TailwindCSS + Zustand |
| 后端框架 | Python FastAPI + Agno Agent 框架 |

---

## 技术栈速览

### 后端（`python/`）

| 技术 | 版本/说明 |
|------|-----------|
| Python | 3.12+ |
| FastAPI | HTTP 服务框架，支持 SSE 流 |
| Uvicorn | ASGI 服务器 |
| Agno | Agent 框架（Agno by A2A Protocol） |
| a2a-sdk | Agent2Agent 协议 SDK |
| SQLite | 本地对话历史持久化（`valuecell.db`） |
| yfinance | 雅虎财经行情数据 |
| akshare | A 股/港股行情数据 |
| Pydantic v2 | 数据校验与序列化 |
| uv | Python 包管理器 |

### 前端（`frontend/`）

| 技术 | 版本/说明 |
|------|-----------|
| React | 19.2 |
| React Router | v7（文件式路由） |
| Zustand | 5.x，全局状态管理 |
| TanStack Query | v5，服务端数据请求 |
| TailwindCSS | v4，原子化样式 |
| shadcn/ui + Radix | UI 组件库 |
| ECharts | 图表库（K 线、折线图等） |
| Vite / rolldown | 构建工具 |
| Bun | 包管理器 / 运行时 |
| Tauri v2 | 可选桌面应用支持 |

---

## 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/ValueCell-ai/valuecell.git
cd valuecell

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENROUTER_API_KEY 等必要参数

# 3. 启动全栈（前端 + 后端 + Agents）
bash start.sh          # Linux / macOS
.\start.ps1            # Windows PowerShell
```

启动后访问：`http://localhost:1420`

---

## 更多文档

- [整体架构](architecture.md)
- [核心概念](concepts.md)
- [使用注意](notes.md)
- [后端核心调度层](backend/core/README.md)
- [数据适配器](backend/adapters/README.md)
- [HTTP 服务端](backend/server/README.md)
- [内置 Agent](backend/agents/README.md)
- [前端页面](frontend/pages/README.md)
- [Agent 对话组件](frontend/agent-chat/README.md)
- [状态管理](frontend/state/README.md)
- [示例说明](examples/README.md)
