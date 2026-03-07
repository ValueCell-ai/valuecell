# Agent 连接管理

路径：`python/valuecell/core/agent/`

该模块负责管理后端与各 Remote Agent 之间的连接，包括 Agent 描述解析、HTTP 客户端连接、通知监听器等。

---

## 模块文件

| 文件 | 类/函数 | 职责 |
|------|---------|------|
| `card.py` | `parse_local_agent_card_dict()`, `find_local_agent_card_by_agent_name()` | 解析 JSON AgentCard 文件 |
| `client.py` | `AgentClient` | A2A 协议 HTTP 客户端 |
| `connect.py` | `RemoteConnections`, `AgentContext` | Agent 连接池管理 |
| `listener.py` | `NotificationListener` | 接收远端 Agent 主动推送的监听器 |
| `decorator.py` | `@agent_handler` | 将普通函数包装为 Agent 处理器 |
| `responses.py` | `streaming.*` | Agent 响应工厂方法 |

---

## AgentCard（Agent 描述卡片）

**文件**：`card.py`，配置文件：`python/configs/agent_cards/*.json`

AgentCard 是 A2A 协议定义的 Agent 元数据对象，描述 Agent 的能力、技能、URL 等信息。

### JSON 格式示例

```json
{
  "name": "InvestmentResearchAgent",
  "display_name": "Investment Research Agent",
  "url": "http://localhost:10014/",
  "description": "综合投研报告生成...",
  "capabilities": {
    "streaming": true,
    "push_notifications": false
  },
  "skills": [
    {
      "id": "research",
      "name": "Research",
      "description": "分析股票基本面...",
      "examples": ["分析 AAPL 的财务状况"],
      "tags": ["research", "fundamentals"]
    }
  ],
  "enabled": true,
  "metadata": {
    "version": "1.0.0",
    "author": "ValueCell Team",
    "tags": ["research"]
  }
}
```

### 解析逻辑

`parse_local_agent_card_dict()` 在解析时会：
1. 移除非标准字段（`enabled`, `metadata`, `display_name`）
2. 填充缺省字段（`description`, `capabilities`, `version` 等）
3. 使用 Pydantic `AgentCard.model_validate()` 校验

### 加载时机

`RemoteConnections._load_remote_contexts()` 在首次需要 Agent 时（懒加载）扫描 `python/configs/agent_cards/` 目录：
- 只加载 `enabled: true` 的 Agent
- 只加载有有效 `url` 的 Agent

---

## AgentClient

**文件**：`client.py`

封装了 A2A SDK 的 HTTP 客户端，负责向远端 Agent 发送消息并接收流式响应。

```python
client = AgentClient(url="http://localhost:10014/", push_notification_url=None)
await client.ensure_initialized()  # 连接并获取 AgentCard

# 发送消息（流式）
async for remote_task, event in await client.send_message(
    query,
    conversation_id=conversation_id,
    metadata=metadata,
    streaming=True,
):
    # event: TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None
    ...
```

---

## RemoteConnections（连接池）

**文件**：`connect.py`

统一管理所有 Remote Agent 的连接状态，支持懒加载和并发安全的连接建立。

### AgentContext 数据结构

```python
@dataclass
class AgentContext:
    name: str
    url: Optional[str]
    local_agent_card: Optional[AgentCard]
    client: Optional[AgentClient]       # HTTP 客户端
    listener_task: Optional[asyncio.Task]  # 通知监听器任务
    listener_url: Optional[str]         # 监听器 URL
```

### 关键方法

| 方法 | 说明 |
|------|------|
| `start_agent(agent_name)` | 连接到 Agent（懒加载，带锁防并发） |
| `get_client(agent_name)` | 获取 AgentClient（按需启动） |
| `get_agent_card(agent_name)` | 获取 AgentCard |
| `get_all_agent_cards()` | 获取所有已加载的 AgentCard（供 Planner 使用） |
| `list_available_agents()` | 列出所有已配置的 Agent 名称 |
| `list_running_agents()` | 列出当前已连接的 Agent |
| `stop_agent(agent_name)` | 断开连接并清理资源 |
| `stop_all()` | 停止所有连接 |

### 连接建立流程

```
start_agent("ResearchAgent")
    │  获取 agent_lock（防并发重复连接）
    ▼
_get_or_create_context("ResearchAgent")
    │  懒加载：扫描 JSON 文件填充 _contexts
    ▼
_ensure_client(ctx)
    │  AgentClient(url) → ensure_initialized()
    │  获取 Agent 远端的 AgentCard（含 capabilities）
    ▼
[可选] _ensure_listener(ctx)
    │  若 Agent 支持 push_notifications
    ▼
返回 AgentCard
```

---

## NotificationListener

**文件**：`listener.py`

当 Remote Agent 配置了 `push_notifications: true` 时，Core 层会启动一个轻量级 HTTP 服务器监听推送通知。

```python
listener = NotificationListener(
    host="localhost",
    port=5000,
    notification_callback=my_callback,
)
listener_task = asyncio.create_task(listener.start_async())
# 监听 http://localhost:5000/notify
```

---

## Agent 装饰器

**文件**：`decorator.py`

将一个普通的 `BaseAgent` 子类包装为 A2A 兼容的 HTTP 服务，使其可以被 `AgentClient` 调用：

```python
from valuecell.core.agent.decorator import create_agent_app

app = create_agent_app(agent_instance, agent_card)
# 启动 uvicorn 运行 app 即可提供 A2A 兼容接口
```

---

## 响应工厂（streaming 模块）

**文件**：`responses.py`

Agent 实现中用于生成标准化 `StreamResponse` 的工厂函数：

```python
from valuecell.core.agent.responses import streaming

yield streaming.message_chunk("Hello, ")     # 文本 chunk
yield streaming.tool_call_started(id, name)   # 工具调用开始
yield streaming.tool_call_completed(result, id, name)  # 工具调用完成
yield streaming.done()                        # 流结束信号
```
