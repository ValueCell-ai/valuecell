# 任务管理（Task）

路径：`python/valuecell/core/task/`

Task 是 Orchestrator 派发给 Remote Agent 的原子执行单元。TaskManager 管理 Task 的状态转换和生命周期。

---

## 数据模型

### Task

```python
@dataclass
class Task:
    task_id: str                    # 自动生成的唯一 ID
    conversation_id: str            # 所属对话（可能是子对话）
    thread_id: str                  # 所属 thread
    user_id: str                    # 发起用户
    agent_name: str                 # 目标 Agent 名称
    query: str                      # 发给 Agent 的具体问题
    status: TaskStatus              # 状态
    pattern: TaskPattern            # 执行模式
    remote_task_ids: List[str]      # 远端 A2A task ID 列表
    handoff_from_super_agent: bool  # 是否由 SuperAgent 转交
```

### TaskStatus 状态机

```
PENDING ──► RUNNING ──► COMPLETED
                │
                └──► FAILED
                │
                └──► CANCELLED
```

| 状态 | 说明 |
|------|------|
| `PENDING` | 已创建，等待执行 |
| `RUNNING` | 正在向远端 Agent 发送请求 |
| `COMPLETED` | 远端 Agent 成功返回 |
| `FAILED` | 执行失败（网络、Agent 错误等） |
| `CANCELLED` | 手动取消（如对话关闭） |

### TaskPattern（执行模式）

| 模式 | 说明 | 用途 |
|------|------|------|
| `ONCE` | 执行一次 | 常规查询 |
| `RECURRING` | 周期执行 | 定期推送通知（如价格告警） |

---

## TaskManager

**文件**：`manager.py`

内存中的 Task 状态机管理器（任务不持久化，仅在内存中跟踪生命周期）。

### 关键方法

| 方法 | 说明 |
|------|------|
| `update_task(task)` | 注册/更新 Task |
| `start_task(task_id)` | 设置为 RUNNING |
| `complete_task(task_id)` | 设置为 COMPLETED |
| `fail_task(task_id, reason)` | 设置为 FAILED |
| `cancel_task(task_id)` | 设置为 CANCELLED |
| `cancel_conversation_tasks(conversation_id)` | 取消某对话下所有活跃 Task |
| `get_task(task_id)` | 获取 Task 对象 |
| `list_tasks(conversation_id)` | 列出对话下所有 Task |

### 并发安全

TaskManager 内部使用 `asyncio.Lock` 保证状态转换的原子性。

---

## Task 与 Conversation 的关系

- **普通模式**（`handoff_from_super_agent=False`）：Task 的 `conversation_id` 与主对话相同，所有消息写入同一对话
- **SuperAgent 转交模式**（`handoff_from_super_agent=True`）：每个 Task 创建一个**新的子对话**（`generate_conversation_id()`），在前端展示为可展开/折叠的子对话区域（`subagent_conversation` 组件类型）

```
主对话 (conversation_id = "conv-001")
    ├── thread_started
    ├── subagent_conversation (start, agent="ResearchAgent", sub_conv_id="conv-002")
    │     ├── [子对话 conv-002 的消息...]
    │     └── subagent_conversation (end)
    └── done
```

---

## 与 Orchestrator 的交互

```python
# 注册 Task
await self.task_manager.update_task(task)

# 开始执行
await self.task_manager.start_task(task_id)

# 完成
await self.task_manager.complete_task(task_id)

# 失败
await self.task_manager.fail_task(task_id, str(e))

# 对话关闭时取消所有 Task
await self.task_manager.cancel_conversation_tasks(conversation_id)
```
