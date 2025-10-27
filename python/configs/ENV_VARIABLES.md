# Environment Variables Guide

## Configuration Priority

ValueCell uses a three-tier configuration system:

1. **Environment Variables** (Highest Priority) - Runtime overrides
2. **.env File** (Middle Priority) - User configuration
3. **YAML Files** (Lowest Priority) - System defaults

## Quick Start

### Minimal Setup (OpenRouter Only)

```bash
# In your .env file
OPENROUTER_API_KEY=sk-or-v1-your-key-here
PROJECT_ROOT=/Users/yourusername/Project/valuecell
```

That's it! All agents will work with OpenRouter's default models.

## Core Configuration

### Application Settings

```bash
APP_ENVIRONMENT=development          # development, staging, production
PROJECT_ROOT=/path/to/valuecell      # Project root directory
DEBUG=false                          # Enable debug mode
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
```

### Model Provider API Keys

Setting a provider's API key enables all models from that provider.

```bash
# OpenRouter (Recommended - unified API for multiple providers)
OPENROUTER_API_KEY=sk-or-v1-...
YOUR_SITE_URL=https://github.com/ValueCell-ai/valuecell
YOUR_SITE_NAME=ValueCell

# Google Gemini
GOOGLE_API_KEY=AIzaSy...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-10-21

# OpenAI Direct
OPENAI_API_KEY=sk-...

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek
DEEPSEEK_API_KEY=sk-...
```

## Agent-Specific Overrides

### Research Agent

Override model and parameters for the Research Agent:

```bash
RESEARCH_AGENT_MODEL_ID=anthropic/claude-3.5-sonnet
RESEARCH_AGENT_PROVIDER=openrouter
RESEARCH_AGENT_TEMPERATURE=0.8
RESEARCH_AGENT_MAX_TOKENS=8192
RESEARCH_AGENT_EMBEDDING_MODEL=text-embedding-3-small
RESEARCH_AGENT_LOG_LEVEL=DEBUG
```

### SEC Agent

```bash
SEC_AGENT_MODEL_ID=google/gemini-2.5-flash
SEC_AGENT_PROVIDER=openrouter
SEC_AGENT_PARSER_MODEL=openai/gpt-4o-mini
```

### Trading Agent

```bash
TRADING_AGENT_MODEL_ID=openai/gpt-4o
TRADING_AGENT_PROVIDER=openrouter
```

### Auto Trading Agent

```bash
AUTO_TRADING_AGENT_PARSER_MODEL=openai/gpt-4o-mini
```

## Third-Party Integration Configuration

### TradingAgents

```bash
# LLM Provider
TRADINGAGENTS_LLM_PROVIDER=openai
TRADINGAGENTS_DEEP_THINK_LLM=o4-mini
TRADINGAGENTS_QUICK_THINK_LLM=gpt-4o-mini
TRADINGAGENTS_BACKEND_URL=https://api.openai.com/v1

# Embeddings (Required if using OpenRouter)
EMBEDDER_BASE_URL=https://api.openai.com/v1
EMBEDDER_MODEL_ID=text-embedding-3-small

# Analysis Parameters
TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
TRADINGAGENTS_MAX_RISK_DISCUSS_ROUNDS=1
TRADINGAGENTS_ONLINE_TOOLS=true
```

### AI-Hedge-Fund

```bash
AI_HEDGE_FUND_PARSER_MODEL_ID=openai/gpt-4o-mini
```

## Advanced Configuration

### Provider Selection

ValueCell automatically detects which provider to use based on available API keys.

```bash
# Auto-detection (default behavior)
# Just set any provider's API key and it will be auto-selected
# Priority: azure > openrouter > anthropic > google > deepseek

# Disable auto-detection if needed
AUTO_DETECT_PROVIDER=false

# Explicitly override primary provider
PRIMARY_PROVIDER=openrouter

# Override fallback chain
FALLBACK_PROVIDERS=google,anthropic
```

### Global Model Parameters

```bash
MODEL_TEMPERATURE=0.7
MODEL_MAX_TOKENS=4096
MODEL_TOP_P=1.0
MODEL_TIMEOUT=60
```

### Server Configuration

```bash
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
CORS_ORIGINS=http://localhost:1420,http://localhost:3000
```

## Agent API Keys (Data Sources)

Additional API keys for data sources (not model providers):

```bash
# Financial Data
SEC_EDGAR_API_KEY=...
FINANCIAL_DATASETS_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
POLYGON_API_KEY=...
FINNHUB_API_KEY=...

# News APIs
NEWS_API_KEY=...
```

## Usage Examples

### Example 1: Default Setup (OpenRouter)

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-abc123
PROJECT_ROOT=/Users/you/valuecell
```

All agents use OpenRouter with default models from `providers/openrouter.yaml`.

### Example 2: Override Research Agent to Use Claude

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-abc123
RESEARCH_AGENT_MODEL_ID=anthropic/claude-3.5-sonnet
```

Research Agent now uses Claude, other agents still use their defaults.

### Example 3: Use Google Direct (Not via OpenRouter)

```bash
# .env
GOOGLE_API_KEY=AIzaSy...
RESEARCH_AGENT_PROVIDER=google
RESEARCH_AGENT_MODEL_ID=gemini-2.5-pro
```

Research Agent connects directly to Google (bypassing OpenRouter).

### Example 4: Production with Azure (Auto-Detection)

```bash
# .env
APP_ENVIRONMENT=production
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://prod.openai.azure.com
```

Azure will be **automatically selected** as the primary provider (highest priority in auto-detection).
All agents use Azure OpenAI by default without explicitly setting PRIMARY_PROVIDER.

### Example 4b: Production with Azure (Explicit)

```bash
# .env
APP_ENVIRONMENT=production
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://prod.openai.azure.com
PRIMARY_PROVIDER=azure  # Optional: Explicit override disables auto-detection
```

Same result, but explicitly sets Azure (useful if you have multiple providers configured).

### Example 5: High Temperature for Creative Research

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-abc123
RESEARCH_AGENT_TEMPERATURE=0.95
RESEARCH_AGENT_MAX_TOKENS=16384
```

Override just the parameters, keep default model.

## Provider Auto-Detection

### How It Works

ValueCell intelligently selects the best provider based on your configured API keys:

1. **Check for explicit override**: If `PRIMARY_PROVIDER` is set, use it
2. **Auto-detect from API keys**: Check which providers have valid API keys
3. **Select by priority**: Choose the first available provider in this order:
   - **Azure** (enterprise-grade, recommended for production)
   - **OpenRouter** (unified API, easiest for development)
   - **Anthropic** (direct Claude access)
   - **Google** (direct Gemini access)
   - **DeepSeek** (cost-effective alternative)
4. **Fallback to config**: Use `primary_provider` from config.yaml

### Examples

**Scenario 1: Only OpenRouter key configured**
```bash
OPENROUTER_API_KEY=sk-or-...
```
→ Auto-selects: `openrouter`

**Scenario 2: Both Azure and OpenRouter configured**
```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
OPENROUTER_API_KEY=sk-or-...
```
→ Auto-selects: `azure` (higher priority)

**Scenario 3: Multiple providers, explicit override**
```bash
AZURE_OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
PRIMARY_PROVIDER=openrouter  # Force OpenRouter despite Azure being available
```
→ Uses: `openrouter` (explicit override wins)

**Scenario 4: Disable auto-detection**
```bash
AZURE_OPENAI_API_KEY=...
AUTO_DETECT_PROVIDER=false
```
→ Uses: `openrouter` (from config.yaml default)

### Benefits

- **Zero configuration**: Just add your API key, it works automatically
- **Smart defaults**: Enterprise providers (Azure) preferred over unified APIs
- **Flexible override**: Can always explicitly set provider if needed
- **Transparent**: Logs show which provider was selected and why

## Configuration Details

### 1. YAML Defines Capabilities

In `providers/openrouter.yaml`:

```yaml
default_model: "google/gemini-2.5-flash"
models:
  - id: "google/gemini-2.5-flash"
    context_window: 1048576
    cost_per_1m_tokens: 0.075
```

### 2. Agent YAML Sets Preferences

In `agents/research_agent.yaml`:

```yaml
models:
  primary:
    model_id: "google/gemini-2.5-flash"
    provider: "openrouter"
    parameters:
      temperature: 0.7
      max_tokens: 8192
```

### 3. .env Overrides Everything

```bash
# User sets this, overrides agent YAML
RESEARCH_AGENT_MODEL_ID=anthropic/claude-3.5-sonnet
```

### 4. Code Reads Final Config

```python
from valuecell.config.loader import load_agent_config

config = load_agent_config("research_agent")
# Returns merged config with all overrides applied
model_id = config["models"]["primary"]["model_id"]
# Result: "anthropic/claude-3.5-sonnet" (from .env)
```

## Benefits

1. **Users**: Just set API keys in `.env`, everything works
2. **Developers**: Pre-configure optimal settings in agent YAML
3. **DevOps**: Override anything at runtime via environment variables
4. **System**: Maintain provider capabilities in YAML registry

## Troubleshooting

### Agent Not Working?

Check configuration priority:

```bash
# 1. Check if API key is set
echo $OPENROUTER_API_KEY

# 2. Validate agent config
python -m valuecell.config.validate research_agent

# 3. Check logs
tail -f logs/*/backend.log
```

### Which Model Is Being Used?

```python
from valuecell.config.loader import load_agent_config

config = load_agent_config("research_agent")
print(f"Model: {config['models']['primary']['model_id']}")
print(f"Provider: {config['models']['primary']['provider']}")
```

## Best Practices

1. **Development**: Use free models from OpenRouter
   ```bash
   OPENROUTER_API_KEY=...
   RESEARCH_AGENT_MODEL_ID=google/gemini-2.0-flash-exp:free
   ```

2. **Production**: Use reliable paid models
   ```bash
   OPENROUTER_API_KEY=...
   RESEARCH_AGENT_MODEL_ID=google/gemini-2.5-flash
   ```

3. **Testing**: Override in CI/CD
   ```bash
   export RESEARCH_AGENT_MODEL_ID=mock-model
   export PRIMARY_PROVIDER=mock
   ```

4. **Cost Control**: Use cheaper models for parsing
   ```bash
   SEC_AGENT_PARSER_MODEL=openai/gpt-4o-mini
   ```

## See Also

- [config.yaml](config.yaml) - Main configuration
- [providers/openrouter.yaml](providers/openrouter.yaml) - OpenRouter capabilities
- [agents/research_agent.yaml](agents/research_agent.yaml) - Agent configuration

