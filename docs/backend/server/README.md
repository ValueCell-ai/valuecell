# HTTP 服务端（Server API）

路径：`python/valuecell/server/`

ValueCell 的后端 HTTP 服务基于 FastAPI 构建，提供 RESTful API 和 SSE 流式接口。

---

## 目录结构

```
valuecell/server/
├── main.py                      # uvicorn 启动入口
├── api/
│   ├── app.py                   # FastAPI 应用工厂
│   ├── exceptions.py            # 异常处理器
│   ├── routers/                 # 路由模块
│   │   ├── agent.py             # Agent 信息接口
│   │   ├── agent_stream.py      # SSE 流式接口
│   │   ├── conversation.py      # 对话管理接口
│   │   ├── watchlist.py         # 观察列表接口
│   │   ├── user_profile.py      # 用户 Profile 接口
│   │   ├── i18n.py              # 国际化接口
│   │   └── system.py            # 系统信息接口
│   └── schemas/                 # Pydantic 请求/响应模型
├── config/
│   ├── settings.py              # 配置（从环境变量读取）
│   └── i18n.py                  # 国际化配置
├── db/
│   ├── connection.py            # SQLAlchemy 连接
│   ├── init_db.py               # 自动建表
│   └── models/                  # ORM 模型
│       ├── agent.py             # Agent 表
│       ├── asset.py             # 资产表
│       ├── watchlist.py         # 观察列表表
│       └── user_profile.py      # 用户 Profile 表
│   └── repositories/            # 数据库访问层
└── services/                    # 业务逻辑层
    ├── agent_stream_service.py  # 调用 Orchestrator 产生 SSE
    ├── agent_service.py         # Agent 列表/详情服务
    ├── conversation_service.py  # 对话历史服务
    ├── assets/
    │   └── asset_service.py     # 资产行情服务
    └── user_profile_service.py  # 用户 Profile 服务
```

---

## API 路由总览

所有接口的 URL 前缀为 `/api/v1`。

### Agent 相关

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/agents` | 获取所有可用 Agent 列表 |
| `GET` | `/api/v1/agents/{agent_name}` | 获取单个 Agent 详情 |
| `POST` | `/api/v1/agents/stream` | **SSE 流式对话接口**（主要接口） |

### 对话历史

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/conversations` | 获取用户对话列表 |
| `GET` | `/api/v1/conversations/{conversation_id}` | 获取单个对话详情 |
| `GET` | `/api/v1/conversations/{conversation_id}/history` | 获取对话历史消息 |
| `DELETE` | `/api/v1/conversations/{conversation_id}` | 删除对话 |

### 观察列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/watchlist` | 获取用户观察列表 |
| `POST` | `/api/v1/watchlist` | 创建观察列表 |
| `POST` | `/api/v1/watchlist/items` | 添加股票到观察列表 |
| `DELETE` | `/api/v1/watchlist/items/{ticker}` | 从观察列表移除 |
| `GET` | `/api/v1/watchlist/prices` | 批量获取观察列表价格 |
| `GET` | `/api/v1/stocks/search` | 搜索股票/资产 |
| `GET` | `/api/v1/stocks/{ticker}` | 获取资产详情 |
| `GET` | `/api/v1/stocks/{ticker}/sparkline` | 获取 Sparkline 数据 |

### 用户 Profile

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/user/profile` | 获取用户 Profile |
| `PUT` | `/api/v1/user/profile` | 更新用户 Profile |
| `GET` | `/api/v1/user/memory` | 获取用户 Memory 条目 |
| `DELETE` | `/api/v1/user/memory/{memory_id}` | 删除 Memory 条目 |

### 系统与 I18n

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 应用信息（name, version, environment） |
| `GET` | `/api/v1/system/health` | 健康检查 |
| `GET` | `/api/v1/i18n/languages` | 获取支持的语言列表 |
| `PUT` | `/api/v1/i18n/language` | 切换当前语言 |

---

## SSE 流式接口详解

**路径**：`POST /api/v1/agents/stream`
**文件**：`api/routers/agent_stream.py`

### 请求体

```json
{
  "query": "分析苹果公司最新财报",
  "agent_name": "InvestmentResearchAgent",
  "conversation_id": "conv-uuid-xxx"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户输入文本 |
| `agent_name` | string | 否 | 指定目标 Agent；为空时路由到 SuperAgent |
| `conversation_id` | string | 否 | 对话 ID；为空时自动生成 |

### 响应格式

响应 `Content-Type: text/event-stream`，每行格式：

```
data: {"event": "message_chunk", "data": {"conversation_id": "...", "thread_id": "...", "task_id": "...", "item_id": "...", "role": "agent", "payload": {"content": "Hello"}}}\n\n
```

### 请求生命周期

1. FastAPI 创建 `StreamingResponse`
2. `AgentStreamService.stream_query_agent()` 调用 `AgentOrchestrator.process_user_input()`
3. Orchestrator 生成器 yield `BaseResponse` 对象
4. Router 将每个 `BaseResponse` 序列化为 JSON，格式化为 SSE 格式

---

## 异常处理

| 异常类型 | HTTP 状态码 | 说明 |
|----------|-------------|------|
| `APIException` | 4xx/5xx（可配置） | 业务逻辑异常 |
| `RequestValidationError` | 422 | Pydantic 请求校验失败 |
| `Exception`（通用） | 500 | 未预期异常 |

---

## 数据库层

### ORM 模型（`db/models/`）

| 表 | 模型 | 字段概要 |
|----|------|----------|
| `agents` | `AgentModel` | name, display_name, enabled, metadata, created_at |
| `assets` | `AssetModel` | ticker, asset_type, names, market_info |
| `watchlists` | `WatchlistModel` | user_id, name, tickers, is_default |
| `user_profiles` | `UserProfileModel` | user_id, language, timezone, memory |

### Repository 层（`db/repositories/`）

提供 CRUD 操作的封装，隔离 ORM 与 Service 层：

```python
# 示例
repo = WatchlistRepository(session)
watchlists = await repo.get_user_watchlists(user_id)
```

---

## 配置（`config/settings.py`）

所有配置从环境变量读取，使用 `@lru_cache()` 缓存单例：

```python
settings = get_settings()

settings.API_HOST          # 默认 "0.0.0.0"
settings.API_PORT          # 默认 8000
settings.API_DEBUG         # 默认 false（true 时开启 /docs）
settings.DATABASE_URL      # SQLite 路径
settings.CORS_ORIGINS      # 允许的 CORS 来源
settings.LOCALE_DIR        # 多语言文件目录
```
