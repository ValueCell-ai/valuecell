# 内置 Agent 概览

路径：`python/valuecell/agents/`，`python/valuecell/third_party/`

ValueCell 内置多种专业投资与交易 Agent，每个 Agent 作为独立的 HTTP 服务运行，通过 A2A 协议与 Core 调度层交互。

---

## Agent 架构

每个 Agent 遵循统一的实现模式：

```
Agent HTTP Server（A2A 兼容）
    │  基于 valuecell.core.agent.decorator
    │  监听指定端口
    ▼
BaseAgent 子类
    │  实现 stream() 和可选的 notify() 方法
    ▼
Agno Agent（内部 LLM 推理）
    │  工具调用、知识库查询
    ▼
数据源（SEC EDGAR / Web / 行情数据等）
```

### BaseAgent 抽象接口

```python
class BaseAgent(ABC):
    async def stream(self, query, conversation_id, task_id, dependencies)
        -> AsyncGenerator[StreamResponse, None]:
        """用户触发的流式响应（SSE）"""

    async def notify(self, query, conversation_id, task_id, dependencies)
        -> AsyncGenerator[NotifyResponse, None]:
        """Agent 主动触发的推送（如定期报告/价格告警）"""
```

---

## Agent 列表

| Agent | 端口 | 文件路径 | 功能 |
|-------|------|----------|------|
| [ResearchAgent](research-agent.md) | 10014 | `agents/research_agent/` | SEC 文件分析 + Web 搜索 + 知识库问答 |
| [AutoTradingAgent](auto-trading-agent.md) | 10013 | `agents/auto_trading_agent/` | 加密货币自动交易（Binance / 模拟盘） |
| [AI Hedge Fund Agents](ai-hedge-fund.md) | 10011~10020 | `third_party/ai-hedge-fund/` | 多投资大师风格（BenGraham / Buffett / ...） |
| InvestmentResearchAgent | 10014 | `third_party/TradingAgents/` | 综合投研报告 |

---

## Agent Card 配置

每个 Agent 在 `python/configs/agent_cards/` 目录下有对应的 JSON 配置文件。Planner 通过扫描这些文件来了解可用的 Agent 能力。

### 配置字段说明

```json
{
  "name": "ResearchAgent",           // 唯一标识，与代码中的 name 一致
  "display_name": "Research Agent",  // 前端展示名称
  "url": "http://localhost:10014/",  // Agent HTTP 服务地址
  "description": "...",             // Agent 能力描述（影响 Planner 路由决策）
  "capabilities": {
    "streaming": true,               // 是否支持流式输出
    "push_notifications": false      // 是否支持主动推送通知
  },
  "skills": [                        // 技能列表（影响 Planner 路由决策）
    {
      "id": "research",
      "name": "Research",
      "description": "...",
      "examples": ["分析 AAPL..."],  // 用于帮助 Planner 理解何时使用
      "tags": ["research"]
    }
  ],
  "enabled": true,                   // false 时不被 Planner 发现
  "metadata": { "version": "1.0.0" }
}
```

---

## 依赖（Dependencies）注入

每次 Task 执行时，Orchestrator 将用户的上下文信息作为 `dependencies` 传入 Agent：

```python
metadata[DEPENDENCIES] = {
    USER_PROFILE: {              # 用户 Profile（语言偏好、Memory 等）
        "language": "zh-Hans",
        "timezone": "Asia/Shanghai",
        "memory": [...]
    },
    CURRENT_CONTEXT: {},         # 当前执行上下文（扩展预留）
    LANGUAGE: "zh-Hans",         # 当前语言
    TIMEZONE: "Asia/Shanghai",   # 当前时区
}
```

Agent 在 `build_ctx_from_dep(dependencies)` 中解析并注入到 Agno Agent 的上下文。

---

## 响应组件类型

Agent 除了输出普通文本外，还可以通过 `component_generator` 事件推送结构化 UI 组件：

```python
# 生成研究报告组件
yield streaming.component(
    ComponentType.REPORT,
    ReportComponentData(
        title="AAPL 财报分析",
        data="...",           # Markdown 内容
        create_time="2025-01-01 10:00:00"
    )
)

# 生成可过滤折线图
yield streaming.component(
    ComponentType.FILTERED_LINE_CHART,
    FilteredLineChartComponentData(
        title="价格走势",
        data="[['日期', 'BTC价格'], ['2025-01-01', 50000], ...]",
        create_time="..."
    )
)
```

---

## 添加新 Agent

1. 创建 Agent 实现类（继承 `BaseAgent`）
2. 创建启动脚本（`__main__.py`），使用 `create_agent_app()` 包装并启动 HTTP 服务
3. 在 `python/configs/agent_cards/` 添加对应的 JSON Card 文件（`enabled: true`）
4. 在 `start.sh` 中添加启动命令
5. 重启服务后，Planner 会自动发现新 Agent

---

## 详细文档

- [Research Agent](research-agent.md)
- [Auto Trading Agent](auto-trading-agent.md)
- [AI Hedge Fund Agents](ai-hedge-fund.md)
