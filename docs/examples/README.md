# 使用示例

本文介绍 ValueCell 的典型使用场景，帮助快速理解系统的端到端工作流程。

---

## 示例 1：与 Research Agent 对话分析股票

### 场景

用户想了解苹果公司最新财报情况。

### 操作步骤

1. 在前端访问 `/market`，找到 `Research Agent` 卡片，点击进入
2. 在对话框输入：**"分析苹果公司（AAPL）2024年年报，关注营收和利润变化"**
3. 系统自动处理并流式输出结果

### 后端处理流程

```
前端 POST /api/v1/agents/stream
  { query: "分析苹果...", agent_name: "InvestmentResearchAgent" }
    │
    ▼
AgentOrchestrator.process_user_input()
  └── 创建新 thread → yield thread_started
    │
    ▼
ExecutionPlanner（Agno Agent + LLM）
  └── 解析需求 → 生成 ExecutionPlan
  TaskItem:
    - agent_name: "InvestmentResearchAgent"
    - query: "Analyze AAPL 2024 annual report..."
    │
    ▼
RemoteConnections.start_agent("InvestmentResearchAgent")
  └── A2A HTTP 连接到 localhost:10014
    │
    ▼
ResearchAgent.stream()
  ├── yield tool_call_started("fetch_periodic_sec_filings")
  ├── [SEC EDGAR 获取 10-K 文件]
  ├── yield tool_call_completed(result)
  ├── yield tool_call_started("web_search")
  ├── [搜索最新分析师报告]
  ├── yield tool_call_completed(result)
  └── yield message_chunk * N（流式输出分析报告）
```

### 前端展示

- 工具调用显示为可折叠的 `ToolCallRenderer` 条目（显示正在查询 SEC 文件）
- 分析报告通过 `MarkdownRenderer` 流式打字机效果输出
- 如果 Agent 生成了报告组件（`component_type: "report"`），会在右侧显示完整报告

---

## 示例 2：使用 SuperAgent 进行通用问答

### 场景

用户不知道应该使用哪个 Agent，直接在通用入口提问。

### 操作步骤

访问 `/agent/ValueCellAgent`（通用入口），输入：**"巴菲特的价值投资原则是什么？"**

### 处理流程

```
AgentOrchestrator
  └── user_input.target_agent_name == "ValueCellAgent"
    │
    ▼
SuperAgent.run(user_input)
  ├── Agno Agent 分析意图
  └── 决策: ANSWER（直接回答，不需要专业 Agent）
    │
    ▼
直接输出回答（message_chunk 流）
  （不经过 Planner，不调用 Remote Agent）
```

### 转交 Planner 的情况

如果用户输入：**"帮我分析一下 NVDA 最近的投资价值"**

```
SuperAgent.run()
  └── 决策: HANDOFF_TO_PLANNER
       enriched_query: "Analyze NVDA investment value including fundamentals, technicals and valuation"
    │
    ▼
ExecutionPlanner.create_plan()
  └── 路由到 WenBuffettAgent 或 AswathDamodaranAgent
```

---

## 示例 3：HITL（Human-in-the-Loop）交互

### 场景

Planner 发现用户请求信息不完整，需要澄清。

### 操作步骤

用户输入：**"帮我买一些股票"**（信息不完整）

### 处理流程

```
ExecutionPlanner.create_plan()
  └── Agno Agent 检测到信息不足
       UserControlFlowTools 触发（或 LLM 主动请求）
    │
    ▼
UserInputRequest(prompt="请告诉我您想买哪只股票，以及投资金额？")
    │
    ▼
前端收到 plan_require_user_input 事件
  └── 显示提示："请告诉我您想买哪只股票，以及投资金额？"
    │
用户回复: "买 BTC，投入 1000 USDT"
    │
    ▼
Orchestrator.provide_user_input(conversation_id, "买 BTC，投入 1000 USDT")
  └── UserInputRequest.provide_response() → asyncio.Event.set()
    │
    ▼
Planner 恢复执行
  └── 生成完整 ExecutionPlan → 路由到 AutoTradingAgent
```

---

## 示例 4：观察列表（Watchlist）管理

### 场景

用户在首页添加股票到自选列表并查看实时行情。

### 操作步骤

1. 访问 `/home`，点击搜索图标
2. 在 `StockSearchModal` 中搜索 "腾讯"
3. 选择 `HKEX:00700`，添加到 Watchlist

### 前端请求流程

```typescript
// 1. 搜索股票
POST /api/v1/stocks/search
{ query: "腾讯", limit: 10 }
// → AdapterManager 并行查询 AKShare + YFinance
// → 返回 [{ ticker: "HKEX:00700", names: ["腾讯控股"], ... }]

// 2. 添加到 Watchlist
POST /api/v1/watchlist/items
{ ticker: "HKEX:00700" }
// → WatchlistRepository 写入 SQLite

// 3. 首页展示
GET /api/v1/watchlist/prices
// → AdapterManager.get_multiple_prices(["HKEX:00700", ...])
// → 并行从 AKShare 获取所有价格
// → 返回 { "HKEX:00700": { current_price: 385.0, change_percent: 1.2, ... } }
```

### 实时数据刷新

前端使用 TanStack Query 定时刷新：
```typescript
const { data } = useQuery({
  queryKey: ["watchlist-prices"],
  queryFn: stockApi.getWatchlistPrices,
  refetchInterval: 60 * 1000,  // 每分钟刷新
});
```

---

## 示例 5：查看对话历史

### 场景

用户重新打开页面，想继续之前与 Research Agent 的对话。

### 处理流程

```
前端加载 /agent/InvestmentResearchAgent
    │
    ▼
GET /api/v1/conversations?agent_name=InvestmentResearchAgent
  → 返回对话列表（按 updated_at 排序）
    │
用户点击历史对话 "conv-001"
    │
    ▼
GET /api/v1/conversations/conv-001/history
  → 后端调用 AgentOrchestrator.get_conversation_history(conv-001)
  → 从 SQLite 读取 ConversationItem 列表
  → 通过 ResponseFactory 转换为 BaseResponse 列表
  → 返回 SSEData[] 格式
    │
    ▼
前端 dispatchAgentStoreHistory(conversationId, history)
  → batchUpdateAgentConversationsStore() 批量重建状态树
    │
    ▼
ChatThreadArea 渲染完整历史对话
```

---

## 示例 6：添加自定义 Agent

### 场景

开发者想要添加一个新的 Agent（如"技术分析 Agent"）。

### 实现步骤

**第 1 步**：实现 Agent 类

```python
# python/valuecell/agents/my_agent/core.py
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.core.agent.responses import streaming

class MyTechnicalAgent(BaseAgent):
    async def stream(self, query, conversation_id, task_id, dependencies):
        # 你的业务逻辑
        yield streaming.message_chunk("分析中...")
        # ... 调用技术指标工具
        yield streaming.message_chunk("RSI: 65，处于中性区间")
        yield streaming.done()
```

**第 2 步**：创建启动脚本

```python
# python/valuecell/agents/my_agent/__main__.py
import uvicorn
from valuecell.core.agent.decorator import create_agent_app
from .core import MyTechnicalAgent

agent = MyTechnicalAgent()
app = create_agent_app(agent, agent_card)  # agent_card 从 JSON 文件加载

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10020)
```

**第 3 步**：添加 Agent Card

```json
// python/configs/agent_cards/my_technical_agent.json
{
  "name": "MyTechnicalAgent",
  "display_name": "Technical Analysis Agent",
  "url": "http://localhost:10020/",
  "description": "专业的技术分析...",
  "skills": [...],
  "enabled": true
}
```

**第 4 步**：在 `start.sh` 添加启动命令

```bash
uv run python -m valuecell.agents.my_agent &
```

**第 5 步**：重启服务

Planner 会自动发现新 Agent，并在适合的场景下路由请求到该 Agent。
