# 前端页面（Pages）

路径：`frontend/src/app/`

ValueCell 前端基于 React Router v7 构建，使用文件式路由（file-based routing）。

---

## 路由配置

**文件**：`frontend/src/routes.ts`

```typescript
export default [
  index("app/redirect-to-home.tsx"),           // "/" → 重定向到 /home

  ...prefix("/home", [
    layout("app/home/_layout.tsx", [
      index("app/home/home.tsx"),               // "/home" → 行情主页
      route("/stock/:stockId", "app/home/stock.tsx"), // "/home/stock/NASDAQ:AAPL" → 股票详情
    ]),
  ]),

  route("/market", "app/market/agents.tsx"),    // "/market" → Agent 市场

  ...prefix("/agent", [
    route("/:agentName", "app/agent/chat.tsx"),  // "/agent/ResearchAgent" → 对话页面
    route("/:agentName/config", "app/agent/config.tsx"), // 配置页
  ]),

  ...prefix("/setting", [
    layout("app/setting/_layout.tsx", [
      index("app/setting/memory.tsx"),          // "/setting" → 设置/Memory
    ]),
  ]),
]
```

---

## 各页面说明

### 1. Home（行情主页）`/home`

**文件**：`app/home/home.tsx`，`app/home/_layout.tsx`

**功能**：

- **Sparkline 股票列表**（`SparklineStockList`）：展示用户 Watchlist 中的股票，每个卡片显示名称、价格、涨跌幅和迷你折线图
- **股票详情列表**（`StockDetailsList`）：展示更详细的行情信息
- **股票搜索**（`StockSearchModal`）：搜索并添加股票到 Watchlist
- **Agent 建议**（`AgentSuggestionsList`）：推荐可用的 Agent

**侧边栏**（`AppSidebar`）：导航菜单 + 对话历史列表

#### 数据请求

```typescript
// 使用 TanStack Query 获取 Watchlist 数据
const { data: watchlist } = useQuery({
  queryKey: ["watchlist"],
  queryFn: () => stockApi.getWatchlist(),
});

// 使用自定义 Hook 获取 Sparkline 数据
const { sparklineStocks } = useSparklineStocks(watchlistTickers);
```

---

### 2. Stock 详情页 `/home/stock/:stockId`

**文件**：`app/home/stock.tsx`

**功能**：

- 展示单只股票的详细行情（价格、涨跌幅、成交量等）
- K 线图 / 折线图展示历史价格
- 基本信息（公司简介、行业、市值等）

---

### 3. Market（Agent 市场）`/market`

**文件**：`app/market/agents.tsx`

**功能**：

- 展示所有可用的 Agent 卡片列表（`AgentCard`）
- 每个卡片显示 Agent 名称、描述、能力标签
- 点击进入对应的 Agent 对话页面

#### 数据请求

```typescript
// 从后端获取 Agent 列表
const { data: agents } = useQuery({
  queryKey: ["agents"],
  queryFn: () => agentApi.getAgents(),
});
```

---

### 4. Agent 对话页 `/agent/:agentName`

**文件**：`app/agent/chat.tsx`

**功能**：

- 与指定 Agent 进行实时流式对话
- 展示对话历史（从后端恢复）
- 流式渲染 Agent 的回复（文本/组件/工具调用等）
- 支持多种消息类型的渲染（Markdown/报告/折线图等）

**子组件详见**：[Agent 对话界面文档](../agent-chat/README.md)

---

### 5. Agent 配置页 `/agent/:agentName/config`

**文件**：`app/agent/config.tsx`

**功能**：

- 配置特定 Agent 的参数（如 AutoTradingAgent 的交易对、资金等）

---

### 6. Setting（设置页）`/setting`

**文件**：`app/setting/memory.tsx`，`app/setting/_layout.tsx`

**功能**：

- **Memory 管理**：查看和删除 Agent 记忆的用户偏好信息
- 每条 Memory 显示为 `MemoryItemCard`

---

## 共享布局组件

### AppSidebar（`components/valuecell/app-sidebar.tsx`）

全局侧边栏，包含：
- 应用导航（Home / Market / Setting）
- 当前 Agent 的对话历史列表（`AppConversationSheet`）
- 菜单项（`agent-menus.tsx`, `stock-menus.tsx`）

### AppConversationSheet（`components/valuecell/app-conversation-sheet.tsx`）

侧边栏中展开的对话历史面板，显示历史对话列表，支持：
- 切换历史对话
- 删除历史对话

---

## Skeleton 加载态

所有页面均有对应的骨架屏（Skeleton）状态，防止数据加载期间页面空白：

| 骨架屏 | 文件 | 对应页面 |
|--------|------|----------|
| `SparklineStockListSkeleton` | `skeleton/sparkline-stock-list-skeleton.tsx` | Home 行情列表 |
| `AgentMarketSkeleton` | `skeleton/agent-market-skeleton.tsx` | Market 页 |
