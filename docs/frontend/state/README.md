# 前端状态管理与 SSE 通信

路径：`frontend/src/store/`, `frontend/src/lib/`, `frontend/src/hooks/`

---

## 整体状态架构

```
SSEClient（lib/sse-client.ts）
    │  解析后端 SSE 事件
    ▼
useSSE hook（hooks/use-sse.ts）
    │  处理连接状态、错误
    ▼
useAgentStore（store/agent-store.ts）
    │  Zustand 全局状态
    │  dispatchAgentStore(action: SSEData)
    ▼
updateAgentConversationsStore（lib/agent-store.ts）
    │  纯函数：将 SSE 事件更新到状态树
    ▼
AgentConversationsStore 状态树
    │  { [conversationId]: ConversationView }
    ▼
React 组件订阅 → 重新渲染
```

---

## SSEClient（`lib/sse-client.ts`）

基于 `fetch` + `ReadableStream` 实现的 SSE 客户端，支持自定义 Headers（解决原生 `EventSource` 不支持 POST 和自定义 Headers 的局限）。

### 特性

- **POST 请求**：支持发送 JSON body（原生 EventSource 仅支持 GET）
- **自定义 Headers**：支持认证 Token 等
- **连接状态管理**：`CONNECTING / OPEN / CLOSED` 三态
- **超时处理**：握手超时（默认 30 秒）
- **容错解析**：使用 `best-effort-json-parser` 解析不完整 JSON（流式传输中可能出现截断）

### 使用方式

```typescript
const client = new SSEClient(
  {
    url: "/api/v1/agents/stream",
    timeout: 30000,
  },
  {
    onData: (data: SSEData) => {
      store.dispatchAgentStore(data);
    },
    onOpen: () => console.log("Connected"),
    onClose: () => console.log("Closed"),
    onError: (err) => console.error(err),
  }
);

await client.connect(JSON.stringify({ query, agent_name, conversation_id }));

// 关闭连接
client.close();
// 清理资源
client.destroy();
```

---

## useSSE Hook（`hooks/use-sse.ts`）

封装 `SSEClient`，提供 React 友好的 API：

```typescript
const { isStreaming, sendMessage } = useSSE({
  url: "/api/v1/agents/stream",
  agentName: "ResearchAgent",
  conversationId: "conv-xxx",
  onData: (data) => dispatch(data),
});

// 发送消息（建立 SSE 连接）
await sendMessage("分析苹果公司财报");
```

### 状态说明

| 状态 | 说明 |
|------|------|
| `isStreaming` | 是否正在接收流（控制输入框 disabled 状态）|

---

## useAgentStore（`store/agent-store.ts`）

Zustand store，管理所有对话的状态树。

### 状态结构

```typescript
interface AgentStoreState {
  agentStore: AgentConversationsStore;  // { [conversationId]: ConversationView }
  curConversationId: string;            // 当前激活的对话 ID
}

// AgentConversationsStore 的数据形状
{
  "conv-001": {
    threads: {
      "thread-001": {
        tasks: {
          "task-001": {
            items: [ChatItem, ChatItem, ...]
          }
        }
      }
    },
    sections: {
      "filtered_line_chart": [ChatItem, ...]  // 右侧组件区数据
    }
  }
}
```

### Actions

| Action | 说明 |
|--------|------|
| `dispatchAgentStore(action: SSEData)` | 处理单条 SSE 事件，更新状态树 |
| `dispatchAgentStoreHistory(conversationId, history)` | 批量加载历史记录（页面刷新后恢复） |
| `setCurConversationId(id)` | 切换当前对话 |
| `resetStore()` | 重置所有状态 |

### 选择器 Hook

```typescript
// 获取当前对话数据
const { curConversation, curConversationId } = useCurrentConversation();

// 获取指定对话数据
const conversation = useConversationById("conv-001");

// 获取操作方法（避免不必要渲染）
const { dispatchAgentStore, setCurConversationId } = useAgentStoreActions();
```

---

## updateAgentConversationsStore（`lib/agent-store.ts`）

纯函数（使用 [mutative](https://github.com/unadlib/mutative) 实现不可变更新），将 SSE 事件映射到状态树的正确位置：

### 事件处理逻辑

```typescript
function updateAgentConversationsStore(
  store: AgentConversationsStore,
  action: SSEData
): AgentConversationsStore {
  switch (action.event) {
    case "thread_started":
      // 在对应 conversation 下创建新 thread
      store[conversationId].threads[threadId] = { tasks: {} };

    case "task_started":
      // 在 thread 下创建新 task
      store[conversationId].threads[threadId].tasks[taskId] = { items: [] };

    case "message_chunk":
      // 追加文本到现有 item（相同 item_id），或创建新 item
      const existingItem = findItemById(items, item_id);
      if (existingItem) {
        existingItem.payload.content += content;  // 打字机效果
      } else {
        items.push(newChatItem);
      }

    case "component_generator":
      // 特殊组件类型（report/filtered_line_chart 等）
      // 部分类型放入 conversation.sections（右侧区域）
      // 部分类型放入 thread 内联显示
      if (isSectionType(component_type)) {
        store[conversationId].sections[component_type].push(item);
      } else {
        items.push(item);
      }

    case "tool_call_started":
    case "tool_call_completed":
      // 工具调用条目（相同 item_id 合并为一条）
      ...
  }
}
```

---

## API 客户端（`lib/api-client.ts`）

封装 `fetch` 的通用 HTTP 客户端，用于非 SSE 的 REST 请求：

```typescript
const apiClient = createApiClient({ baseURL: "/api/v1" });

// GET 请求
const agents = await apiClient.get<AgentInfo[]>("/agents");

// POST 请求
const result = await apiClient.post("/watchlist/items", { ticker: "NASDAQ:AAPL" });
```

---

## API 模块（`api/`）

各业务域的 API 封装：

| 文件 | 函数 | 说明 |
|------|------|------|
| `api/agent.ts` | `getAgents()`, `getAgent(name)` | Agent 列表/详情 |
| `api/conversation.ts` | `getConversations()`, `getHistory(id)`, `deleteConversation(id)` | 对话管理 |
| `api/stock.ts` | `searchStocks()`, `getWatchlist()`, `addToWatchlist()`, `getSparkline()` | 行情数据 |
| `api/setting.ts` | `getUserProfile()`, `updateProfile()`, `getMemory()`, `deleteMemory(id)` | 用户设置 |

---

## TanStack Query 集成

数据请求使用 TanStack Query（`@tanstack/react-query`）管理缓存和状态：

```typescript
// 查询示例
const { data: agents, isLoading } = useQuery({
  queryKey: ["agents"],
  queryFn: agentApi.getAgents,
  staleTime: 5 * 60 * 1000,  // 5分钟缓存
});

// Mutation 示例
const { mutate: addToWatchlist } = useMutation({
  mutationFn: (ticker) => stockApi.addToWatchlist(ticker),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
});
```

---

## 常量（`constants/`）

| 文件 | 说明 |
|------|------|
| `constants/agent.ts` | `AGENT_COMPONENT_TYPE`（所有组件类型枚举）、`AGENT_SECTION_COMPONENT_TYPE`（右侧区域类型）、`AGENT_MULTI_SECTION_COMPONENT_TYPE`（详情区类型）|
| `constants/api.ts` | API 基础 URL 配置 |
| `constants/stock.ts` | 股票相关常量 |
