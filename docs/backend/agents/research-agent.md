# Research Agent（研究 Agent）

路径：`python/valuecell/agents/research_agent/`
端口：`10014`（默认）

Research Agent 是一个综合性的金融研究助手，整合了 SEC 文件获取、Web 搜索和向量知识库，能够回答关于上市公司基本面、监管文件、市场动态等问题。

---

## 核心功能

| 功能 | 工具 | 说明 |
|------|------|------|
| 定期报告分析 | `fetch_periodic_sec_filings` | 获取 10-K、10-Q 等定期报告 |
| 事件报告分析 | `fetch_event_sec_filings` | 获取 8-K、6-K 等事件型报告 |
| 网络搜索 | `web_search` | 实时搜索最新市场信息 |
| 知识库问答 | `knowledge`（向量库） | 基于预建知识库的深度问答 |

---

## 模块文件

| 文件 | 说明 |
|------|------|
| `core.py` | `ResearchAgent` 主类实现 |
| `sources.py` | 数据源工具（SEC / Web 搜索函数） |
| `knowledge.py` | Agno 向量知识库配置 |
| `prompts.py` | LLM 系统提示和期望输出格式 |
| `schemas.py` | 数据模型 |
| `vdb.py` | 向量数据库配置 |
| `__main__.py` | A2A HTTP 服务启动入口 |

---

## 实现原理

```python
class ResearchAgent(BaseAgent):
    def __init__(self):
        self.knowledge_research_agent = Agent(
            model=get_model("RESEARCH_AGENT_MODEL_ID"),
            tools=[
                fetch_periodic_sec_filings,    # SEC 定期报告
                fetch_event_sec_filings,        # SEC 事件报告
                web_search,                     # Web 搜索
            ],
            knowledge=knowledge,               # 向量知识库
            search_knowledge=True,             # 自动搜索知识库
            add_history_to_context=True,       # 多轮对话历史
        )

    async def stream(self, query, conversation_id, task_id, dependencies):
        response_stream = self.knowledge_research_agent.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,    # 流式输出工具调用过程
        )
        async for event in response_stream:
            if event.event == "RunContent":
                yield streaming.message_chunk(event.content)
            elif event.event == "ToolCallStarted":
                yield streaming.tool_call_started(...)
            elif event.event == "ToolCallCompleted":
                yield streaming.tool_call_completed(...)
```

---

## SEC 工具说明

### fetch_periodic_sec_filings

获取 SEC 定期报告（10-K 年报、10-Q 季报等）：
- 使用 `edgar` 库访问 SEC EDGAR 数据库
- 需要在 `.env` 中配置 `SEC_EMAIL`（SEC 要求标识请求者身份）
- 返回文件的文本内容，供 LLM 分析

### fetch_event_sec_filings

获取 SEC 事件型报告（8-K 重大事件、6-K 外国私人发行人等）：
- 同样使用 `edgar` 库
- 适用于获取公司最新公告、财报发布等事件

---

## 向量知识库

Research Agent 配备了一个向量知识库（`knowledge.py`），可以预加载公司研究报告、行业分析等文档，支持语义检索：

- **嵌入模型**：通过 `EMBEDDER_*` 环境变量配置
- **存储后端**：向量数据库（pgvector 或内存）
- **检索方式**：Agent 在回答问题前自动搜索知识库

> **注意**：若使用 OpenRouter 作为 LLM 提供商，需要单独配置 Embedding 服务（`EMBEDDER_API_KEY`, `EMBEDDER_BASE_URL`, `EMBEDDER_MODEL_ID`），因为 OpenRouter 不支持 Embedding 模型。

---

## 使用示例

```
用户：分析苹果公司 2024 年财报，关注营收增长和利润率变化

ResearchAgent 执行流程：
1. Tool Call: fetch_periodic_sec_filings("AAPL", "10-K", "2024")
2. 解析文件内容，提取关键财务数据
3. Tool Call: web_search("Apple Q4 2024 earnings analysis")
4. 综合 SEC 数据和最新市场分析，生成研究报告
5. 输出 Markdown 格式的综合分析报告
```

---

## 配置

### 必需环境变量

| 变量 | 说明 |
|------|------|
| `RESEARCH_AGENT_MODEL_ID` | Agent 使用的 LLM 模型 ID（默认：`google/gemini-2.5-flash`） |
| `SEC_EMAIL` | SEC EDGAR API 要求的邮箱标识 |

### 可选环境变量（向量知识库）

| 变量 | 说明 |
|------|------|
| `EMBEDDER_API_KEY` | Embedding 服务 API Key |
| `EMBEDDER_BASE_URL` | Embedding 服务 URL |
| `EMBEDDER_MODEL_ID` | Embedding 模型 ID |
| `EMBEDDER_DIMENSION` | Embedding 向量维度（默认 1568） |
