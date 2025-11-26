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
  <a href="README.zh.md" style="color: gray;">中文（简体）</a>
  <a href="README.zh_Hant.md" style="color: auto;">中文（繁體）</a>
  <a href="README.ja.md" style="color: gray;">日本語</a>
</div>


# ValueCell
ValueCell is a community-driven, multi-agent platform for financial applications. Our mission is to build the world's largest decentralized financial agent community.

It provides a team of TOP investment Agents to help you with stock selection, research, tracking, and even trading.

Welcome to join our Discord community to share feedback and issues you encounter, and invite more developers to contribute 🔥🔥🔥

>Note: ValueCell team members will never proactively contact community participants. This project is for technical exchange only. Investing involves risk. ⚠️

# Screenshot

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


# Key Features

<p align="center">
  <img src="assets/architecture.png" style="width: 100%; height: auto;">
</p>


## Multi-Agent System
- **DeepResearch Agent**: Automatically retrieve and analyze fundamental documents to generate accurate data insights and interpretable summaries
- **Strategy Agent**: Supports multiple crypto assets and multi-strategy smart trading, automatically executing your strategies
- **News Retrieval Agent**: Supports personalized scheduled news delivery to track key information in real time
- **Others**: More agents are in planning...

## Flexible Integrations
- **Multiple LLM Providers**: Support OpenRouter, SiliconFlow,Azure,Openai-compatible,Google,OpenAI and DeepSeek
- **Popular Market Data**: Cover US market, Crypto market, Hong Kong market, China market and more
- **Multi-Agent Framework Compatible**: Support Langchain, Agno by A2A Protocol for research and development integration
- **Exchange Connectivity**: Live routing to OKX and Binance, featuring built-in guardrails

# Quick Start

## For Users

To get started quickly, download the latest ValueCell application for MacOS or Windows from the [Releases page](https://github.com/ValueCell-ai/valuecell/releases) on GitHub. You may also download the application from our official website: [https://valuecell.ai](https://valuecell.ai).

After installation, please configure your preferred model provider before using ValueCell for the first time. Refer to the instructions in the application or documentation as needed.

## For Developers
ValueCell is a Python-based application featuring a comprehensive web interface. Follow this guide to set up and run the application efficiently.

### Prerequisites

For optimal performance and streamlined development, we recommend installing the following tools:

**[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Ultra-fast Python package and project manager built in Rust  
**[bun](https://github.com/oven-sh/bun#install)** - High-performance JavaScript/TypeScript toolkit with runtime, bundler, test runner, and package manager

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/ValueCell-ai/valuecell.git
   cd valuecell
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file with your API keys and preferences. This configuration file is shared across all agents. See [Configuration Guide](docs/CONFIGURATION_GUIDE.md) for details.

## Configuration

More detailed configuration information can be found at [CONFIGURATION_GUIDE](./docs/CONFIGURATION_GUIDE.md)

### Model Providers
Configure your preferred model providers by editing the `.env` file:

- **Simple Setup**: Just configure the model provider's API Key

- **Advanced Configuration**: For research-type agents, you need to configure more environment variables. Please refer to the `.env.example` file for details.

- **Official Recommendation**: Configure OpenRouter + any supplier that provides embedding models. Reason: This enables quick model switching across providers and provides RAG+Memory AI capabilities
  

Choose your preferred models and providers based on your requirements and preferences.

## Running the Application

Launch the complete application (frontend, backend, and agents):

### Linux / Macos
```bash
bash start.sh
```

### Windows (PowerShell)
```powershell
.\start.ps1
```

## Accessing the Interface

- **Web UI**: Navigate to [http://localhost:1420](http://localhost:1420) in your browser
- **Logs**: Monitor application logs at `logs/{timestamp}/*.log` for detailed runtime information of backend services and individual agents


## Next Steps

Once the application is running, you can explore the web interface to interact with ValueCell's features and capabilities.

## Live Trading

- Configure AI Models: Add your AI Model API Key through the web interface.
- Configure Exchanges: Set up Binance/HyperLiquid/OKX/Coinbase... API credentials
- Create Strategies: Combine AI model with exchange to create custom strategies
- Monitor & Control: Start/stop traders and monitor performance in real-time

### Supported Exchanges

| Exchange | Notes | Status |
| --- | --- | --- |
| **Binance** | Only supports international site [binance.com](binance.com), not US site. Uses USDT-M futures (USDT-margined contracts). Ensure your futures account has sufficient USDT balance. Trading pair format: `BTC/USDT` | ✅ Tested |
| **Hyperliquid** | Only supports USDC as margin currency. Uses your main wallet address + API wallet private key authentication (use [API tab](https://app.hyperliquid.xyz/API) to apply). Market orders are automatically converted to IoC limit orders. Trading pair format must be manually adjusted to `SYMBOL/USDC` (e.g., `WIF/USDC`) | ✅ Tested |
| **OKX** | Requires API Key, Secret, and Passphrase for authentication. Supports USDT-margined contracts. Trading pair format: `BTC/USDT` | ✅ Tested |
| Coinbase | Supports USDT-margined contracts. Coinbase International is not yet supported | 🟡 Partially Tested |
| Gate.io | Supports USDT-margined contracts. Requires API Key and Secret | 🟡 Partially Tested |
| MEXC | Supports USDT-margined contracts. Requires API Key and Secret | 🟡 Partially Tested |
| Blockchain | Supports USDT-margined contracts. Requires API Key, Secret | 🟡 Partially Tested |

**Legend**:
- ✅ **Tested**: Fully tested and verified in production environment
- 🟡 **Partially Tested**: Code implementation complete but not fully tested, may require debugging
- **Recommended**: Prioritize using fully tested exchanges (Binance, Hyperliquid, OKX)

### Notice
- Currently supports leverage trading only, so you need to ensure your Perps account has sufficient balance.
- You must keep your API secrets secure to avoid losing funds. The app stores secrets locally on your device and will not send them to any third party over the internet.
- To ensure your account safety, you need to reset your API keys regularly. 

---
**Note**: Before running the application, ensure all prerequisites are installed and environment variables are properly configured. If it has been a long time since the last update, you can delete local data stores and start fresh:
- LanceDB directory (stored in your system application directory):
  - macOS: `~/Library/Application Support/ValueCell/lancedb`
  - Linux: `~/.config/valuecell/lancedb`
  - Windows: `%APPDATA%\ValueCell\lancedb`
- Knowledge directory (stored in your system application directory):
  - macOS: `~/Library/Application Support/ValueCell/.knowledge`
  - Linux: `~/.config/valuecell/.knowledge`
  - Windows: `%APPDATA%\ValueCell\.knowledge`
- SQLite database file (stored in your system application directory):
  - macOS: `~/Library/Application Support/ValueCell/valuecell.db`
  - Linux: `~/.config/valuecell/valuecell.db`
  - Windows: `%APPDATA%\ValueCell\valuecell.db`

# Developers

We sincerely invite all developers to join our Discord discussion group, where we regularly share the community roadmap and upcoming contributor benefit plans.

Details on development processes and standards are provided below:[CONTRIBUTING.md](.github/CONTRIBUTING.md)

# Roadmap

## 🤖 Enhanced Agent Capabilities
### Trading Capabilities
- **Crypto**: Supports OKX、Binance and Hyperliquid exchanges, with more exchanges planned for integration...
- **Securities**: Gradually support AI securities trading

### Market Expansion
- **European Markets**: Add support for FTSE, DAX, CAC 40, and other European exchanges
- **Asian Markets**: Expand coverage to Nikkei and emerging Asian markets
- **Commodity Markets**: Oil, Gold, Silver, Agricultural products analysis
- **Forex Markets**: Major currency pairs and cross-currency analysis

### Asset Diversification
- **Fixed Income**: Government bonds, corporate bonds, and yield analysis agents
- **Derivatives**: Options, futures, and complex financial instruments
- **Alternative Investments**: Private equity, hedge funds, and venture capital analysis

### Advanced Notification & Push Types
- **Real-time Alerts**: Price movements, volume spikes, and technical breakouts
- **Scheduled Reports**: Daily/weekly/monthly portfolio summaries
- **Event-driven Notifications**: Earnings releases, dividend announcements, regulatory changes
- **Custom Triggers**: User-defined conditions and thresholds
- **Multi-channel Delivery**: Discord and webhook integrations

## ⚙️ Product Configuration & Personalization
### Multi-platform Products
- **Desktop Support**: Gradually support desktop and client capabilities
- **Database Hot Updates**: Gradually support compatibility upgrades

### Internationalization (i18n)
- **Multi-language Support**: English, Chinese (Simplified/Traditional), Japanese, Korean, Spanish, French
- **Localized Market Data**: Region-specific financial terminology and formats
- **Cultural Adaptation**: Time zones, date formats, and currency preferences
- **Agent Personality Localization**: Culturally appropriate communication styles

### Token & Authentication Management
- **API Key Management**: Secure storage and rotation of third-party API keys
- **OAuth Integration**: Support for major financial data providers

### User Preferences & Customization
- **Investment Profile**: Risk tolerance, investment horizon, and strategy preferences
- **UI/UX Customization**: Dark/light mode, dashboard layouts, and widget preferences
- **Agent Behavior**: Communication frequency, analysis depth, and reporting style
- **Portfolio Management**: Custom benchmarks, performance metrics, and allocation targets

### Memory & Learning Systems
- **Conversation History**: Persistent chat history across sessions
- **User Learning**: Adaptive recommendations based on user behavior
- **Market Memory**: Historical context and pattern recognition
- **Preference Evolution**: Dynamic adjustment of recommendations over time

## 🔧 ValueCell SDK Development
### Core SDK Features
- **Python SDK**: Comprehensive library for agent integration and customization
- **WebSocket Support**: Real-time data streaming and bidirectional communication

### Agent Integration Framework
- **Plugin Architecture**: Easy integration of third-party agents and tools
- **Agent Registry**: Marketplace for community-contributed agents

### Developer Tools & Documentation
- **Interactive API Explorer**: Swagger/OpenAPI documentation with live testing
- **Code Examples**: Sample implementations in multiple programming languages
- **Testing Framework**: Unit tests, integration tests, and mock data providers


# Star History

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
