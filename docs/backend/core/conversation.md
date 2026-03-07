# 对话管理（Conversation）

路径：`python/valuecell/core/conversation/`

对话管理模块负责维护对话元数据和消息条目的存储，提供内存和 SQLite 两种后端实现。

---

## 模块文件

| 文件 | 类 | 职责 |
|------|-----|------|
| `models.py` | `Conversation`, `ConversationStatus` | 对话元数据模型 |
| `conversation_store.py` | `ConversationStore`, `InMemoryConversationStore`, `SQLiteConversationStore` | 对话元数据持久化 |
| `item_store.py` | `ItemStore`, `InMemoryItemStore`, `SQLiteItemStore` | 消息条目持久化 |
| `manager.py` | `ConversationManager` | 高层管理接口，协调两个 Store |

---

## 数据模型

### Conversation（对话元数据）

```python
class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: Optional[str]
    agent_name: Optional[str]
    status: ConversationStatus      # ACTIVE / INACTIVE / REQUIRE_USER_INPUT
    created_at: datetime
    updated_at: datetime
```

### ConversationStatus 状态机

```
ACTIVE  ──────────────────────────────────► INACTIVE
  │                                              ▲
  │ require_user_input()                         │
  ▼                                              │
REQUIRE_USER_INPUT ──── activate() ────────► ACTIVE
```

| 状态 | 说明 |
|------|------|
| `ACTIVE` | 正常活跃状态，可接收新消息 |
| `INACTIVE` | 已停用，不再接收新消息 |
| `REQUIRE_USER_INPUT` | 等待 HITL 用户输入，Orchestrator 会拒绝新的普通请求 |

### ConversationItem（消息条目）

```python
class ConversationItem(BaseModel):
    item_id: str
    role: Role              # USER / AGENT / SYSTEM
    agent_name: Optional[str]
    event: ConversationItemEvent   # 事件类型
    conversation_id: str
    thread_id: Optional[str]
    task_id: Optional[str]
    payload: str            # JSON 序列化的 ResponsePayload
```

---

## 存储后端

### 双后端设计

```
ConversationManager
    ├── conversation_store: ConversationStore
    │     ├── InMemoryConversationStore（测试/开发）
    │     └── SQLiteConversationStore（生产）
    │
    └── item_store: ItemStore
          ├── InMemoryItemStore（测试/开发）
          └── SQLiteItemStore（生产）
```

### 生产配置（Orchestrator 初始化时）

```python
db_path = resolve_db_path()   # 从环境变量 VALUECELL_SQLITE_DB 获取
conversation_manager = ConversationManager(
    conversation_store=SQLiteConversationStore(db_path=db_path),
    item_store=SQLiteItemStore(db_path=db_path),
)
```

---

## ConversationManager API

### 对话元数据操作

| 方法 | 说明 |
|------|------|
| `create_conversation(user_id, title, conversation_id, agent_name)` | 创建新对话 |
| `get_conversation(conversation_id)` | 按 ID 获取对话 |
| `update_conversation(conversation)` | 更新对话元数据 |
| `delete_conversation(conversation_id)` | 删除对话及所有消息 |
| `list_user_conversations(user_id, limit, offset)` | 列出用户对话 |
| `conversation_exists(conversation_id)` | 检查对话是否存在 |

### 状态管理

| 方法 | 说明 |
|------|------|
| `activate_conversation(conversation_id)` | 设置为 ACTIVE |
| `deactivate_conversation(conversation_id)` | 设置为 INACTIVE |
| `require_user_input(conversation_id)` | 设置为 REQUIRE_USER_INPUT |
| `set_conversation_status(conversation_id, status)` | 设置任意状态 |

### 消息条目操作

| 方法 | 说明 |
|------|------|
| `add_item(role, event, conversation_id, ...)` | 添加消息条目 |
| `get_conversation_items(conversation_id, event, component_type)` | 查询消息历史 |
| `get_latest_item(conversation_id)` | 获取最新一条 |
| `get_item(item_id)` | 按 ID 获取单条 |
| `get_item_count(conversation_id)` | 获取消息数量 |
| `get_items_by_role(conversation_id, role)` | 按角色过滤 |

---

## Payload 序列化

`add_item()` 接收 `ResponsePayload`（Pydantic BaseModel），自动调用 `model_dump_json(exclude_none=True)` 序列化为 JSON 字符串存储：

```python
# 存储时
payload_str = payload.model_dump_json(exclude_none=True)

# 读取时（通过 ResponseFactory.from_conversation_item()）
payload_dict = json.loads(item.payload)
response = ResponseFactory.create_from_event_and_payload(item.event, payload_dict)
```

---

## 与 Orchestrator 的交互

Orchestrator 通过 `ResponseBuffer` 的 `flush` 机制将聚合后的内容持久化：

```python
# Orchestrator._persist_items()
for it in items:
    await self.conversation_manager.add_item(
        role=it.role,
        event=it.event,
        conversation_id=it.conversation_id,
        thread_id=it.thread_id,
        task_id=it.task_id,
        payload=it.payload,
        item_id=it.item_id,
        agent_name=it.agent_name,
    )
```
