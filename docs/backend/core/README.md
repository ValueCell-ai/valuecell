# 核心调度层（Core Coordinate）

路径：`python/valuecell/core/coordinate/`

核心调度层是 ValueCell 的"大脑"，负责将用户输入转化为可执行的 Agent 任务序列，并实时流式地将结果返回给调用方。

---

## 模块概览

| 文件 | 类/函数 | 职责 |
|------|---------|------|
| `super_agent.py` | `SuperAgent` | 前置意图分析，决定直接回答 or 转交 Planner |
| `planner.py` | `ExecutionPlanner` | LLM 驱动的任务规划，支持 HITL |
| `orchestrator.py` | `AgentOrchestrator` | 整个生命周期的协调器 |
| `response_buffer.py` | `ResponseBuffer` | 流式 chunk 段落级聚合与稳定 ID 管理 |
| `response_router.py` | `ResponseRouter` | 事件路由，触发持久化副作用 |
| `response.py` | `ResponseFactory` | 各类 `BaseResponse` 工厂方法 |
| `models.py` | `ExecutionPlan`, `PlannerResponse` | 规划数据模型 |

---

## SuperAgent

**文件**：`super_agent.py`

SuperAgent 是请求处理的第一道"分流器"。当用户在没有指定具体 Agent 的情况下（即对话入口是通用的 `ValueCellAgent`）提问时，SuperAgent 先行运行：

```python
class SuperAgentDecision(str, Enum):
    ANSWER = "answer"                    # SuperAgent 直接回答
    HANDOFF_TO_PLANNER = "handoff_to_planner"  # 转交 Planner 规划
```

- **工具**：配备 `Crawl4aiTools`（网页爬取），可实时获取网络信息
- **直接回答场景**：简单问候、一般性金融知识问答
- **转交场景**：需要调用专业 Agent（分析股票、执行交易等）时

```python
# SuperAgent 使用 Agno Agent + LLM 推理
response = await self.agent.arun(
    user_input.query,
    session_id=user_input.meta.conversation_id,
    user_id=user_input.meta.user_id,
    add_history_to_context=True,
)
# 返回 SuperAgentOutcome(decision, answer_content, enriched_query, reason)
```

---

## ExecutionPlanner

**文件**：`planner.py`

Planner 将用户的自然语言需求转化为结构化的 `ExecutionPlan`（由多个 `Task` 组成）。

### 核心流程

```python
plan = await planner.create_plan(user_input, user_input_callback, thread_id)
```

1. 创建 Agno Agent（携带 `tool_get_enabled_agents` 工具）
2. Agent 调用 `tool_get_enabled_agents()` 获取所有可用 Agent 的 AgentCard
3. LLM 根据用户需求和 Agent 能力列表，输出 `PlannerResponse`（JSON Schema 强制格式）
4. 将 `PlannerResponse.tasks` 转换为 `Task` 对象列表

### HITL 支持

若 Agent 运行时 `run_response.is_paused == True`（Agno 的 HITL 机制），Planner 会：
1. 遍历 `tools_requiring_user_input`，每个字段创建一个 `UserInputRequest`
2. 调用 `user_input_callback(request)` 注册到 Orchestrator
3. `await request.wait_for_response()` 阻塞直到用户回复
4. 填入用户回复后调用 `agent.continue_run()` 恢复执行

### PlannerResponse 结构

```python
class PlannerResponse(BaseModel):
    adequate: bool       # 信息是否充分
    reason: str          # 判断依据
    tasks: List[TaskItem]  # 任务列表

class TaskItem(BaseModel):
    agent_name: str      # 目标 Agent 名称
    query: str           # 发给该 Agent 的具体问题
    pattern: TaskPattern  # ONCE / RECURRING
```

---

## AgentOrchestrator

**文件**：`orchestrator.py`

Orchestrator 是整个系统的中枢，管理从用户输入到最终响应的完整生命周期。

### 主入口

```python
async def process_user_input(user_input: UserInput) -> AsyncGenerator[BaseResponse, None]:
```

#### 执行路径

```
用户输入
  │
  ├── conversation 不存在 → create_conversation() → yield conversation_started
  │
  ├── conversation.status == REQUIRE_USER_INPUT
  │     └── _handle_conversation_continuation()  （HITL 恢复路径）
  │
  └── 普通新请求
        └── _handle_new_request()
              │
              ├── [无 target_agent_name] SuperAgent.run()
              │     ├── ANSWER → 直接 yield 回答
              │     └── HANDOFF_TO_PLANNER → 更新 query，继续规划
              │
              └── ExecutionPlanner.create_plan()
                    └── _execute_plan_with_input_support(plan)
                          └── 串行执行每个 Task
                                └── _execute_task_with_input_support(task)
```

### 关键状态管理

| 属性 | 类型 | 作用 |
|------|------|------|
| `user_input_manager` | `UserInputManager` | 管理等待用户回复的 HITL 请求 |
| `_execution_contexts` | `Dict[str, ExecutionContext]` | 被 HITL 暂停的执行上下文，TTL 1 小时 |
| `conversation_manager` | `ConversationManager` | 对话元数据 + 消息条目存储 |
| `task_manager` | `TaskManager` | Task 状态机管理 |
| `agent_connections` | `RemoteConnections` | Remote Agent 连接池 |
| `_response_buffer` | `ResponseBuffer` | 流式 chunk 段落聚合 |

### 公开 API

| 方法 | 说明 |
|------|------|
| `process_user_input()` | 处理新用户输入（SSE 流） |
| `provide_user_input()` | 提供 HITL 用户回复 |
| `has_pending_user_input()` | 检查是否有等待回复的请求 |
| `get_user_input_prompt()` | 获取等待回复的提示文字 |
| `close_conversation()` | 关闭对话并清理资源 |
| `get_conversation_history()` | 获取持久化的历史记录 |
| `cleanup()` | 清理过期上下文，停止所有连接 |

---

## ResponseBuffer

**文件**：`response_buffer.py`

将流式 `message_chunk` 事件聚合为"段落"级别再持久化，避免 SQLite 产生大量碎片化记录，同时为前端提供稳定的 `item_id`（用于流式打字效果的原地更新）。

### 工作原理

```
收到 message_chunk(content="Hello")
    │ annotate(response) → 返回带稳定 item_id 的 response
    ▼
BufferEntry.parts.append("Hello")

收到 message_chunk(content=" world")
    │ annotate(response) → 返回同一 item_id
    ▼
BufferEntry.parts.append(" world")

task_completed → flush_task()
    │
    ▼
SaveItem(item_id, content="Hello world") → 写入 SQLite
```

---

## 相关文档

- [Agent 连接管理](agent-connection.md)
- [对话管理](conversation.md)
- [任务管理](task.md)
