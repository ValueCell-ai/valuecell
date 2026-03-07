# Agent 对话界面组件

路径：`frontend/src/app/agent/components/chat-conversation/`

Agent 对话界面是 ValueCell 最核心的前端模块，负责展示与 Agent 的实时流式对话。

---

## 组件树

```
ChatConversationArea（入口，包裹 MultiSectionProvider）
├── ChatConversationHeader          -- Agent 头像、名称、状态
├── ChatWelcomeScreen               -- 无消息时的欢迎页
├── ChatThreadArea                  -- 对话主体（线程列表）
│   └── ChatItemArea（每个 thread）
│       └── [各类消息渲染器]
│           ├── MarkdownRenderer    -- 普通文本
│           ├── ReportRenderer      -- 研究报告
│           ├── ToolCallRenderer    -- 工具调用日志
│           ├── SecFeedRenderer     -- SEC 报告
│           ├── ModelTradeRenderer  -- 模型交易信号
│           └── ChatConversationRenderer -- 子对话展开
├── ChatInputArea                   -- 输入框 + 发送按钮
├── ChatSectionComponent（右侧栏）  -- 特殊组件侧边展示（如交易图表）
│   └── [SectionComponentType 渲染器]
└── ChatMultiSectionComponent（详情视图）-- 点击展开的详情区
```

---

## 各组件说明

### ChatConversationArea

**文件**：`chat-conversation-area.tsx`

顶层容器，包裹 `MultiSectionProvider`，根据是否有消息历史决定显示欢迎页还是对话区：

```typescript
const hasMessages = currentConversation?.threads &&
  Object.keys(currentConversation.threads).length > 0;

if (!hasMessages) {
  return <ChatWelcomeScreen ... />;
}

return (
  <div className="flex flex-1 gap-2 overflow-hidden">
    <section> {/* 主区域 */}
      <ChatConversationHeader />
      <ChatThreadArea threads={...} />
      <ChatInputArea />
    </section>
    {/* 右侧特殊组件区域（如折线图） */}
    {sections && Object.entries(sections).map(([type, items]) =>
      <ChatSectionComponent componentType={type} items={items} />
    )}
    {/* 详情弹出区 */}
    {currentSection && <ChatMultiSectionComponent />}
  </div>
);
```

### ChatThreadArea

**文件**：`chat-thread-area.tsx`

渲染所有 thread（按时间顺序），每个 thread 包含一次完整的问答交互：
- 显示用户问题（`thread_started` 事件的 payload）
- 显示 Agent 回复（各 task 的消息流）
- 流式输出时显示 `ChatStreamingIndicator`（打字中动画）

### ChatItemArea

**文件**：`chat-item-area.tsx`

渲染单个 thread 内的所有消息条目（`ChatItem[]`），按 `component_type` 分发到对应渲染器：

```typescript
switch (item.component_type) {
  case "message_chunk": return <MarkdownRenderer />;
  case "report":        return <ReportRenderer />;
  case "tool_call_started":
  case "tool_call_completed": return <ToolCallRenderer />;
  case "sec_feed":      return <SecFeedRenderer />;
  case "subagent_conversation": return <ChatConversationRenderer />;
  case "filtered_line_chart":   return <SectionComponentRenderer />;
  // ...
}
```

### ChatInputArea

**文件**：`chat-input-area.tsx`

消息输入框，支持：
- 多行文本输入（`ScrollTextarea`）
- `Enter` 发送，`Shift+Enter` 换行
- `disabled` 状态（流式输出期间禁止发送）
- `variant="chat"` 和 `variant="welcome"` 两种外观

### ChatSectionComponent

**文件**：`chat-section-component.tsx`

右侧特殊组件区域，渲染 `SectionComponentType` 类型的消息（如 `filtered_line_chart`、`filtered_card_push_notification`）。点击某个条目可在 `ChatMultiSectionComponent` 中展开详情。

### ChatWelcomeScreen

**文件**：`chat-welcome-screen.tsx`

首次进入 Agent 对话时的欢迎页，包含 Agent 介绍和输入框。

---

## 渲染器（Renderers）

路径：`frontend/src/components/valuecell/renderer/`

| 渲染器 | 文件 | 适用场景 |
|--------|------|----------|
| `MarkdownRenderer` | `markdown-renderer.tsx` | 普通文本，支持 GFM Markdown |
| `ReportRenderer` | `report-renderer.tsx` | Agent 生成的结构化研究报告（带标题、时间戳） |
| `ToolCallRenderer` | `tool-call-renderer.tsx` | 工具调用开始/完成的日志（可折叠） |
| `SecFeedRenderer` | `sec-feed-renderer.tsx` | SEC 报告摘要 |
| `ModelTradeRenderer` | `model-trade-renderer.tsx` | 单条交易信号卡片 |
| `ModelTradeTableRenderer` | `model-trade-table-renderer.tsx` | 多条交易信号表格 |
| `ChatConversationRenderer` | `chat-conversation-renderer.tsx` | 子 Agent 对话（可展开/折叠）|
| `UnknownRenderer` | `unknown-renderer.tsx` | 未知类型的兜底渲染 |

---

## 流式渲染机制

### 数据流

```
后端 SSE chunk → useSSE() hook → dispatchAgentStore(action)
    │
    ▼
updateAgentConversationsStore(store, action)
    │  根据 event 类型将数据插入/更新正确位置
    ▼
agentStore[conversationId].threads[threadId].tasks[taskId].items[]
    │
    ▼
React 重新渲染 ChatThreadArea → ChatItemArea → 渲染器
```

### item_id 稳定性

流式输出期间，同一段落的所有 `message_chunk` 拥有相同的 `item_id`，前端通过 `item_id` 找到已存在的 `ChatItem` 并追加内容（而不是创建新条目），实现"打字机效果"。

---

## MultiSectionProvider

**文件**：`frontend/src/provider/multi-section-provider.tsx`

管理右侧详情区的展示状态，当用户点击某个 Section 条目时，`currentSection` 更新并触发 `ChatMultiSectionComponent` 展示详情：

```typescript
const { currentSection, setCurrentSection } = useMultiSection();
```

---

## Agent 头像（AgentAvatar）

**文件**：`components/valuecell/agent-avatar.tsx`

根据 `agent_name` 映射到对应的头像图片（`assets/png/agents/*.png`），包含每位投资大师的头像图片。
