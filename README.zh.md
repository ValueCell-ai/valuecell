<p align="center">
  <img src="assets/valuecell.png" style="width: 100%; height: auto;">
</p>

<div align="center" style="line-height: 2;">
    <a href="https://www.python.org/downloads" target="_blank">
        <img src="https://img.shields.io/badge/python-3.12+-blue.svg"
            alt="Python version"></a>
    <a href="LICENSE" target="_blank">
        <img src="https://img.shields.io/badge/license-Apache2.0-red.svg"
            alt="License: Apache2.0"></a>  
    <br>
    <a href="https://discord.com/invite/84Kex3GGAh" target="_blank">
        <img src="https://img.shields.io/discord/1399603591471435907?logo=discord&labelColor=%20%235462eb&logoColor=%20%23f5f5f5&color=%20%235462eb"
            alt="chat on Discord"></a>
    <a href="https://twitter.com/intent/follow?screen_name=valuecell" target="_blank">
        <img src="https://img.shields.io/twitter/follow/valuecell?logo=X&color=%20%23f5f5f5"
            alt="follow on X(Twitter)"></a>
    <a href="https://www.linkedin.com/company/valuecell/" target="_blank">
        <img src="https://custom-icon-badges.demolab.com/badge/LinkedIn-0A66C2?logo=linkedin-white&logoColor=fff"
            alt="follow on LinkedIn"></a>
    <a href="https://www.facebook.com/people/ValueCell/61581410516790/" target="_blank">
        <img src="https://custom-icon-badges.demolab.com/badge/Facebook-1877F2?logo=facebook-white&logoColor=fff"
            alt="follow on Facebook"></a>
</div>

<div align="center">
  <a href="README.md" style="color: gray;">English</a>
  <a href="README.zh.md" style="color: auto;">中文（简体）</a>
  <a href="README.zh_Hant.md" style="color: gray;">中文（繁體）</a>
  <a href="README.ja.md" style="color: gray;">日本語</a>
</div>


# ValueCell
ValueCell 是一个社区驱动的多智能体金融应用产品，我们的计划是打造全球最大的去中心化金融智能体社区

它将为您提供顶级的投资智能体团队，帮助您完成选股，调研，跟踪和交易

欢迎大家加入Discord社区反馈使用中遇到的问题，以及更多开发者参与共建🔥🔥🔥

>注意：ValueCell团队人员不会主动私信社区参与者，项目仅为技术交流使用，投资有风险。⚠️

# 产品截图

<p align="center">
  <img src="assets/product/homepage.png" style="width: 100%; height: auto;">
</p>


<p align="center">
  <img src="assets/product/superagent.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/AutoTradingAgent.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/Model_Configuration.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/agent_market.png" style="width: 100%; height: auto;">
</p>



# 核心特性

<p align="center">
  <img src="assets/architecture.png" style="width: 100%; height: auto;">
</p>


## 多智能体系统
- **DeepResearch Agent**: 获取并分析股票的基本面文件，输出准确的数据、可解释性的总结
- **Strategy Agent**: 支持多种加密资产、多策略智能交易，自动执行你的策略
- **News Retrieval Agent**: 支持个性化定时任务的新闻推送，及时跟踪关键信息
- **其他智能体**：更多智能体正在规划中...

## 灵活集成
- **多种大语言模型提供商**：支持 OpenRouter、SiliconFlow、Azure、Openai-compatible、Google、OpenAI和DeepSeek
- **热门市场数据**：覆盖美国市场、加密货币市场、香港市场、中国市场等
- **多智能体框架兼容**：通过 A2A 协议，支持 Langchain、Agno 等主流Agent框架，进行研发集成
- **交易所连接**：支持实时路由至 OKX 和 Binance，并内置安全防护机制

# 快速开始

## 给用户

要快速开始，请从 GitHub 的[发布页面](https://github.com/ValueCell-ai/valuecell/releases)下载 MacOS 或 Windows 的最新 ValueCell 应用程序。您也可以从我们的官方网站 [https://valuecell.ai](https://valuecell.ai) 下载应用程序。

安装后，初次使用 ValueCell 前请配置您首选的模型提供商。请参考应用程序内的说明或文档。

## 给开发者
ValueCell 是一个基于Python的应用程序，且有完备的前端操作页面。可以参考下面配置快速运行。

### 前提条件

为了获得最佳性能和简化开发，我们建议安装以下工具：

**[uv](https://docs.astral.sh/uv/getting-started/installation/)** - 用Rust构建的超快速Python包和项目管理器  
**[bun](https://github.com/oven-sh/bun#install)** - 高性能JavaScript/TypeScript工具包，集成运行时、打包器、测试运行器和包管理器

### 安装

1. **克隆仓库**

   ```bash
   git clone https://github.com/ValueCell-ai/valuecell.git
   cd valuecell
   ```

2. **配置环境变量**

   ```bash
   cp .env.example .env
   ```
   
   使用您的API密钥和偏好设置编辑`.env`文件。此配置文件在所有智能体之间共享。详见 [配置指南](docs/CONFIGURATION_GUIDE.md)

### 配置

更多系统配置详情说明可以参考[CONFIGURATION_GUIDE](./docs/CONFIGURATION_GUIDE.md)

### 模型提供商
通过编辑`.env`文件配置您首选的模型提供商：

- **简易配置**：仅需配置模型厂商API Key即可

- **其他配置**：对于调研类型的Agent来说，需要配置更多环境变量，可以仔细阅读`.env.example`中的说明

- **官方推荐**：配置OpenRouter + 任意提供嵌入模型的供应商。原因：可以快速实现多厂商模型切换，以及RAG+Memory的AI能力

## 运行应用程序

启动完整的应用程序（前端、后端和智能体）：

### Linux / Macos
```bash
bash start.sh
```

### Windows (PowerShell)
```powershell
.\start.ps1
```

## 访问界面

- **Web UI**：在浏览器中导航到 [http://localhost:1420](http://localhost:1420)
- **日志**：在 `logs/{timestamp}/*.log` 监控应用程序日志，获取后端服务和各个智能体的详细运行时信息

### 下一步

应用运行后，你可以通过网页界面探索并使用 ValueCell 的各项功能和能力。

## 实时交易

- 配置 AI 模型: 通过网页UI界面添加你的 AI 模型 API Key。
- 配置交易所: 设置 Binance/HyperLiquid/OKX/Coinbase... API 凭证
- 创建策略: 将 AI 模型与交易所组合，创建自定义交易策略
- 监控与控制: 实时启动/停止策略，并实时监控交易表现

### 支持的交易所

| 交易所 | 说明 | 状态 |
| --- | --- | --- |
| **Binance** | 仅支持国际站 [binance.com](binance.com)，不支持美国站。使用 USDT-M 合约（USDT 本位合约）。请确保您的合约账户有足够的 USDT 余额。交易对格式：`BTC/USDT` | ✅ 已测试 |
| **Hyperliquid** | 仅支持 USDC 作为保证金货币。使用您的主钱包地址 + API 钱包私钥认证（使用 [API 页面](https://app.hyperliquid.xyz/API) 申请）。市价单会自动转换为 IoC 限价单。交易对格式必须手动调整为 `SYMBOL/USDC`（例如 `WIF/USDC`） | ✅ 已测试 |
| **OKX** | 需要 API Key、Secret 和 Passphrase 进行认证。支持 USDT 本位合约。交易对格式：`BTC/USDT` | ✅ 已测试 |
| Coinbase | 支持 USDT 本位合约。Coinbase International 尚未支持 | 🟡 部分测试 |
| Gate.io | 支持 USDT 本位合约。需要 API Key 和 Secret | 🟡 部分测试 |
| MEXC | 支持 USDT 本位合约。需要 API Key 和 Secret | 🟡 部分测试 |
| Blockchain | 支持 USDT 本位合约。需要 API Key 和 Secret | 🟡 部分测试 |

**图例**:
- ✅ **已测试**: 在生产环境中经过充分测试和验证
- 🟡 **部分测试**: 代码实现已完成但未完全测试，可能需要调试
- **推荐**: 优先使用经过充分测试的交易所（Binance, Hyperliquid, OKX）

### 注意事项
- 目前仅支持杠杆/合约交易，因此您需要确保您的永续合约（Perps）账户有足够的余额。
- 您必须妥善保管您的 API 密钥以避免资金损失。该应用程序将密钥本地存储在您的设备上，不会通过互联网发送给任何第三方。
- 为了确保您的账户安全，您需要定期重置您的 API 密钥。

---

**注意**：运行应用程序前，请确保所有前提条件已安装且环境变量已正确配置
如长时间没有更新，可以删除本地数据并重新启动：
- LanceDB 目录（位于系统应用目录，与 `.env` 同路径）：
  - macOS: `~/Library/Application Support/ValueCell/lancedb`
  - Linux: `~/.config/valuecell/lancedb`
  - Windows: `%APPDATA%\\ValueCell\\lancedb`
- 知识目录（位于系统应用目录，与 `.env` 同路径）：
  - macOS: `~/Library/Application Support/ValueCell/.knowledge`
  - Linux: `~/.config/valuecell/.knowledge`
  - Windows: `%APPDATA%\\ValueCell\\.knowledge`
- SQLite 数据库文件（位于系统应用目录，与 `.env` 同路径）：
  - macOS: `~/Library/Application Support/ValueCell/valuecell.db`
  - Linux: `~/.config/valuecell/valuecell.db`
  - Windows: `%APPDATA%\\ValueCell\\valuecell.db`


# 开发者

诚挚邀请每位开发者加入Discord讨论组，我们会定期交流社区RoadMap以及未来社区贡献者权益规划

开发流程及标准详见:[CONTRIBUTING.md](.github/CONTRIBUTING.md)

# Roadmap

## 🤖 增强智能体能力
### 交易能力
- **加密货币**：支持okx、binance、Hyperliquid交易所，更多交易所规划接入中...
- **证券**：逐步支持AI证券交易

### 市场扩展
- **欧洲市场**：增加对富时指数、DAX、CAC 40和其他欧洲交易所的支持
- **亚洲市场**：扩展对日经指数和新兴亚洲市场的覆盖
- **大宗商品市场**：石油、黄金、白银、农产品分析
- **外汇市场**：主要货币对和交叉货币分析

### 资产类别多样化
- **固定收益**：政府债券、企业债券和收益率分析智能体
- **衍生品**：期权、期货和复杂金融工具
- **另类投资**：私募股权、对冲基金和风险投资分析

### 高级通知和推送类型
- **实时警报**：价格变动、成交量激增和技术突破
- **定期报告**：每日/每周/每月投资组合摘要
- **事件驱动通知**：财报发布、股息公告、监管变化
- **自定义触发器**：用户定义的条件和阈值
- **多渠道推送**：Discord和webhook集成

## ⚙️ 产品配置与个性化
### 多端产品化
-- **客户端支持**：逐步支持桌面端、客户端能力
-- **数据库热更新**：逐步支持兼容性升级

### 国际化 (i18n)
- **多语言支持**：英语、中文（简体/繁体）、日语、韩语、西班牙语、法语
- **本地化市场数据**：特定地区的金融术语和格式
- **文化适应**：时区、日期格式和货币偏好
- **智能体个性本地化**：文化适宜的沟通风格

### 令牌和身份验证管理
- **API密钥管理**：第三方API密钥的安全存储和轮换
- **OAuth集成**：支持主要金融数据提供商

### 用户偏好和自定义
- **投资档案**：风险承受能力、投资期限和策略偏好
- **UI/UX自定义**：深色/浅色模式、仪表板布局和小部件偏好
- **智能体行为**：沟通频率、分析深度和报告风格
- **投资组合管理**：自定义基准、绩效指标和配置目标

### 记忆和学习系统
- **对话历史**：跨会话的持久聊天历史
- **用户学习**：基于用户行为的自适应推荐
- **市场记忆**：历史背景和模式识别
- **偏好演进**：推荐的动态调整

## 🔧 ValueCell SDK开发
### 核心SDK功能
- **Python SDK**：用于智能体集成和自定义的核心代码，衔接前后端
- **WebSocket支持**：实时数据流和双向通信

### 智能体集成框架
- **插件架构**：轻松集成第三方智能体和工具
- **智能体注册表**：社区贡献智能体的市场

### 开发者工具和文档
- **交互式API浏览器**：带有实时测试的Swagger/OpenAPI文档
- **代码示例**：多种编程语言的示例实现
- **测试框架**：单元测试、集成测试和模拟数据提供商


# Star

<div align="center">
<a href="https://www.star-history.com/#ValueCell-ai/valuecell&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date" />
   <img alt="TradingAgents Star History" src="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date" style="width: 80%; height: auto;" />
 </picture>
</a>
</div>

<div align="center">
