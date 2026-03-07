# ValueCell 核心概念

本文介绍 ValueCell 中贯穿前后端的核心设计概念，理解这些概念有助于快速定位代码、扩展功能或调试问题。

---

## 1. 对话层次模型（Conversation Hierarchy）

ValueCell 采用四层 ID 体系来唯一标识任意一条消息：

```
conversation_id
  └── thread_id        （用户每次提问产生一个 thread）
        └── task_id    （每个 thread 可能执行多个 task）
              └── item_id  （最小渲染单元：一段文字、一次工具调用等）
```

| 层次 | 说明 | 持久化 |
|------|------|--------|
| `conversation_id` | 与某个 Agent 的完整会话，类似"聊天室" | SQLite `conversations` 表 |
| `thread_id` | 用户一次提问到回复完毕的完整交互 | SQLite `conversation_items` 的字段 |
| `task_id` | Orchestrator 派发给 Remote Agent 的原子执行单元 | 内存 TaskManager |
| `item_id` | 最小持久化/渲染单元，对应一条 `ConversationItem` | SQLite `conversation_items` 表 |

---

## 2. SSE 事件系统（Server-Sent Events）

前后端通过 HTTP SSE（单向流）实时通信。后端的 `POST /api/v1/agents/stream` 接口返回 `text/event-stream`，每个事件格式为：

```
data: {"event": "<event_type>", "data": {...}}\n\n
```

### 事件类型分类

#### 系统生命周期事件（`SystemResponseEvent`）
| 事件 | 触发时机 |
|------|----------|
| `conversation_started` | 新对话首次创建 |
| `thread_started` | 用户每次发消息，新 thread 开始 |
| `plan_require_user_input` | Planner 需要用户补充信息（HITL） |
| `plan_failed` | 规划失败 |
| `system_failed` | 系统级异常 |
| `done` | 整个响应结束 |

#### 任务状态事件（`TaskStatusEvent`）
| 事件 | 触发时机 |
|------|----------|
| `task_started` | Remote Agent 开始执行 |
| `task_completed` | Remote Agent 执行完毕 |
| `task_failed` | Remote Agent 执行失败 |

#### 流式内容事件（`StreamResponseEvent`）
| 事件 | 触发时机 |
|------|----------|
| `message_chunk` | Agent 输出文本 chunk（流式） |
| `tool_call_started` | Agent 调用工具开始 |
| `tool_call_completed` | 工具调用返回结果 |
| `reasoning_started` | Agent 开始推理 |
| `reasoning` | 推理过程中间步骤 |
| `reasoning_completed` | 推理结束 |

#### 组件生成事件（`CommonResponseEvent`）
| 事件 | 触发时机 |
|------|----------|
| `component_generator` | Agent 生成结构化 UI 组件（报告/图表/子对话等） |

---

## 3. Agent2Agent（A2A）协议

ValueCell 使用 Google 的 [A2A 协议](https://github.com/google/a2a-spec) 实现后端与各 Agent 之间的通信。

### 核心概念
- **AgentCard**：描述 Agent 的 JSON 文件，包含 URL、capabilities、skills 等元数据，位于 `python/configs/agent_cards/*.json`
- **AgentClient**：Core 层用于向远端 Agent 发送 A2A 消息的 HTTP 客户端
- **TaskStatusUpdateEvent**：远端 Agent 通过流式 HTTP 返回的状态更新事件
- **Push Notifications**（可选）：远端 Agent 主动推送通知到 Core 层注册的 listener 端口

### 通信流程
```
Orchestrator
    │  client.send_message(query, streaming=True)
    ▼
AgentClient（HTTP POST 到 Agent URL）
    │
    ▼
Remote Agent HTTP Server
    │  yields TaskStatusUpdateEvent（流式）
    ▼
AgentClient 接收并 yield (remote_task, event)
    │
    ▼
Orchestrator 根据 event 类型路由响应
```

---

## 4. Agno Agent 框架

ValueCell 内部使用 [Agno](https://docs.agno.com) 框架构建 Planner、SuperAgent 和具体的业务 Agent。

### 关键特性
| 特性 | 说明 |
|------|------|
| `Agent.run()` / `Agent.arun()` | 同步/异步执行，返回 `RunResponse` |
| `stream=True` | 开启流式输出 |
| `use_json_mode=True` | 强制 Agent 输出 JSON，配合 `output_schema` 做结构化解析 |
| `add_history_to_context=True` | 自动注入历史消息到 LLM 上下文 |
| `enable_session_summaries=True` | 超长对话自动摘要 |
| `tools=[...]` | 为 Agent 注册可调用工具 |
| `knowledge=...` | 向量知识库（用于 ResearchAgent） |
| `db=InMemoryDb()` | Session 持久化后端（内存） |
| `is_paused` | Human-in-the-Loop：Agent 暂停等待用户输入 |

---

## 5. Human-in-the-Loop（HITL）

当 Planner Agent 检测到信息不足或需要用户确认时，会触发 HITL 流程：

```
ExecutionPlanner.create_plan()
    │  run_response.is_paused == True
    ▼
UserInputRequest(prompt)  ← asyncio.Event 驱动的等待对象
    │
    ▼
Orchestrator._handle_user_input_request()  → UserInputManager 注册
    │
    ▼
前端收到 plan_require_user_input 事件 → 显示提示 → 用户回复
    │
    ▼
Orchestrator.provide_user_input(conversation_id, response)
    │  → UserInputRequest.provide_response(response) → asyncio.Event.set()
    ▼
Planner 恢复执行 → 继续 agent.continue_run()
```

---

## 6. ResponseBuffer 流式缓冲

由于 Agent 输出是逐 token 的 chunk 流，直接存储每个 chunk 会产生大量碎片化记录。`ResponseBuffer` 负责将连续 chunk 聚合为"段落"（paragraph）级别的 `ConversationItem` 再持久化：

- 每个"段落"分配一个稳定的 `item_id`（在流式期间不变）
- 前端可以通过相同的 `item_id` 进行原地更新（流式打字效果）
- 当 task 完成时，调用 `flush_task()` 将所有缓冲内容写入 SQLite

---

## 7. 组件类型（ComponentType）

除普通文本消息外，Agent 还可以生成结构化 UI 组件，通过 `component_generator` 事件推送到前端：

| 类型 | 说明 | 前端渲染器 |
|------|------|-----------|
| `report` | 研究报告（Markdown 格式） | `ReportRenderer` |
| `subagent_conversation` | 子 Agent 对话展开/收起 | `ChatSectionComponent` |
| `filtered_line_chart` | 可过滤折线图（交易数据） | ECharts 图表 |
| `filtered_card_push_notification` | 卡片式推送通知 | 推送通知卡片 |

---

## 8. Asset Ticker 格式

ValueCell 使用统一的内部 Ticker 格式：`EXCHANGE:SYMBOL`

| 交易所 | 示例 | 适配器 |
|--------|------|--------|
| `NASDAQ` | `NASDAQ:AAPL` | YFinance |
| `NYSE` | `NYSE:JPM` | YFinance |
| `HKEX` | `HKEX:00700` | AKShare / YFinance |
| `SSE` | `SSE:601398` | AKShare |
| `SZSE` | `SZSE:000001` | AKShare |
| `BSE` | `BSE:835368` | AKShare |
| `CRYPTO` | `CRYPTO:BTC` | YFinance |

---

## 9. 用户 Profile 与国际化

用户 Profile 包含语言、时区、Memory 等设置，每次 Agent 执行时通过 `dependencies` 注入到 Agent 上下文：

```python
metadata[DEPENDENCIES] = {
    USER_PROFILE: user_profile_data,   # 用户个性化设置
    CURRENT_CONTEXT: {},               # 当前上下文（扩展预留）
    LANGUAGE: get_current_language(),  # 如 "en-US" / "zh-Hans"
    TIMEZONE: get_current_timezone(),  # 如 "America/New_York"
}
```

支持语言：`en_US`, `en_GB`, `zh-Hans`, `zh-Hant`
