# Configuration Guide

The ValueCell project uses a **three-tier configuration system** to enable flexible deployment from development to production. This guide covers all aspects of configuring agents, providers, and models.

## Configuration Priority

ValueCell resolves configuration from multiple sources in this order (highest to lowest priority):

1. **Environment Variables** - Runtime overrides (e.g., `OPENROUTER_API_KEY`)
2. **.env File** - User-level configuration (in project root)
3. **YAML Files** - System defaults (in `python/configs/`)

This hierarchy allows you to:
- Set provider credentials via `.env` without modifying code
- Override settings at runtime via environment variables
- Maintain sensible defaults in YAML files

## Quick Start

### Step 1: Get API Keys

ValueCell supports multiple LLM providers. Choose at least one:

| Provider        | Sign Up                                             |
| --------------- | --------------------------------------------------- |
| **OpenRouter**  | [openrouter.ai](https://openrouter.ai/)             |
| **SiliconFlow** | [siliconflow.cn](https://www.siliconflow.cn/)       |
| **Google**      | [ai.google.dev](https://ai.google.dev/)             |
| **OpenAI**      | [platform.openai.com](https://platform.openai.com/) |
| **DashScope**   | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/#/home) |

### Step 2: Configure .env File

Copy the example file and add your API keys:
Edit `.env` and add your credentials:

# In project root
cp .env.example .env

# Or SiliconFlow (best for Chinese models and cost)
Edit `.env` and add your credentials:

# Or Google Gemini
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxx

# Optional: Set primary provider (auto-detected if not set)
PRIMARY_PROVIDER=openrouter
```

### Step 3: Launch Application

```bash
# macOS / Linux
bash start.sh

# Windows PowerShell
.\start.ps1
```

The system will auto-detect available providers based on configured API keys.

> **Note**: If you get database compatibility errors, delete these locations:
> - LanceDB directory (system application directory, same as `.env`):
>   - macOS: `~/Library/Application Support/ValueCell/lancedb`
>   - Linux: `~/.config/valuecell/lancedb`
>   - Windows: `%APPDATA%\\ValueCell\\lancedb`
> - Knowledge directory (system application directory, same as `.env`):
>   - macOS: `~/Library/Application Support/ValueCell/.knowledge`
>   - Linux: `~/.config/valuecell/.knowledge`
>   - Windows: `%APPDATA%\\ValueCell\\.knowledge`
> - SQLite database file (system application directory, same as `.env`):
>   - macOS: `~/Library/Application Support/ValueCell/valuecell.db`
>   - Linux: `~/.config/valuecell/valuecell.db`
>   - Windows: `%APPDATA%\\ValueCell\\valuecell.db`

---

## Configuration System Architecture

### File Structure

```
python/
├── configs/
│   ├── config.yaml                    # Main configuration
│   ├── config.{environment}.yaml      # Environment-specific overrides
│   ├── providers/
│   │   ├── openrouter.yaml           # OpenRouter provider config
│   │   ├── siliconflow.yaml          # SiliconFlow provider config
│   │   ├── dashscope.yaml            # DashScope (Alibaba Cloud) provider config
│   │   └── other_provider.yaml
│   ├── agents/
│   │   ├── super_agent.yaml          # Super Agent configuration
│   │   ├── research_agent.yaml       # Research Agent configuration
│   │   └── auto_trading_agent.yaml   # Auto Trading Agent configuration
│   ├── agent_cards/                  # UI metadata for agents
│   └── locales/                      # Internationalization files
└── valuecell/
    └── config/
        ├── constants.py              # Configuration constants
        ├── loader.py                 # YAML loader with env var resolution
        └── manager.py                # High-level configuration API
```

### How Configuration Resolution Works

#### 1. Provider Configuration Loading

When the system needs a model, it:

1. **Loads provider YAML** (e.g., `configs/providers/openrouter.yaml`)
2. **Resolves `${VAR}` placeholders** in YAML using environment variables
3. **Applies env variable overrides** (e.g., `OPENROUTER_API_KEY` overrides `connection.api_key`)
4. **Returns ProviderConfig** object with resolved values

**Example: OpenRouter Configuration**

```yaml
connection:
  base_url: "https://openrouter.ai/api/v1"
  api_key_env: "OPENROUTER_API_KEY"    # Specifies which env var to use

default_model: "anthropic/claude-haiku-4.5"

defaults:
  temperature: 0.5
  max_tokens: 4096
```

The system automatically reads `OPENROUTER_API_KEY` from `.env` or environment.

#### 2. Agent Configuration Loading

When you create an agent (e.g., `research_agent`), the system:

1. **Loads agent YAML** (e.g., `configs/agents/research_agent.yaml`)
The system automatically reads `OPENROUTER_API_KEY` from `.env` or environment.
3. **Applies environment variable overrides** via `env_overrides` map
4. **Merges with global defaults** from `config.yaml`
5. **Returns AgentConfig** object with complete configuration

**Example: Agent Configuration**

```yaml
name: "Research Agent"
enabled: true

models:
  primary:
    model_id: "google/gemini-2.5-flash"
    provider: "openrouter"
    provider_models:
      siliconflow: "Qwen/Qwen3-235B-A22B-Thinking-2507"
      google: "gemini-2.5-flash"
    parameters:
      temperature: 0.7

env_overrides:
  RESEARCH_AGENT_MODEL_ID: "models.primary.model_id"
  RESEARCH_AGENT_PROVIDER: "models.primary.provider"
```

This allows runtime overrides:

```bash
export RESEARCH_AGENT_MODEL_ID="anthropic/claude-3.5-sonnet"
export RESEARCH_AGENT_PROVIDER="openrouter"
# Now research agent uses Claude 3.5 Sonnet instead of Gemini
```

---

## Detailed Configuration Reference

### Global Configuration (`config.yaml`)

The main configuration file sets system-wide defaults:

```yaml
models:
  # Primary provider used if API keys from multiple providers are available
  primary_provider: "openrouter"
  
  # Global default parameters (used by all models unless overridden)
  defaults:
    temperature: 0.5
    max_tokens: 4096
  
  # Provider registry
  providers:
    openrouter:
      config_file: "providers/openrouter.yaml"
      api_key_env: "OPENROUTER_API_KEY"
    siliconflow:
      config_file: "providers/siliconflow.yaml"
      api_key_env: "SILICONFLOW_API_KEY"
    google:
      config_file: "providers/google.yaml"
      api_key_env: "GOOGLE_API_KEY"
    dashscope:
      config_file: "providers/dashscope.yaml"
      api_key_env: "DASHSCOPE_API_KEY"

# Agent registry
agents:
  super_agent:
    config_file: "agents/super_agent.yaml"
  research_agent:
    config_file: "agents/research_agent.yaml"
  auto_trading_agent:
    config_file: "agents/auto_trading_agent.yaml"
```

### Provider Configuration

Each provider has its own YAML file in `configs/providers/`. Here's the structure:

```yaml
name: "Provider Display Name"
provider_type: "provider_id"           # Used internally
enabled: true                          # Can be disabled without deleting config

# Connection details
connection:
  base_url: "https://api.example.com/v1"
  api_key_env: "PROVIDER_API_KEY"      # Which env var to read
  endpoint_env: "PROVIDER_ENDPOINT"    # Optional: for Azure-style endpoints

# Default model when none specified
default_model: "model-id"

# Default parameters for all models from this provider
defaults:
  temperature: 0.7
  max_tokens: 4096
  top_p: 0.95

# List of available models
models:
  - id: "model-id-1"
    name: "Model Display Name"
    context_length: 128000
    max_output_tokens: 8192
  
  - id: "model-id-2"
    name: "Another Model"
    context_length: 256000

# Embedding configuration (optional, not all providers support it)
embedding:
  default_model: "embedding-model-id"
  
  defaults:
    dimensions: 1536
    encoding_format: "float"
  
  models:
    - id: "embedding-model-id"
      name: "Embedding Model"
      dimensions: 1536
      max_input: 8192

# Provider-specific configuration
extra_headers:
  HTTP-Referer: "https://valuecell.ai"
  X-Title: "ValueCell"
```

### Agent Configuration

Agent YAML files define how agents should be initialized. Key features:

```yaml
name: "Agent Display Name"
enabled: true

# Model configuration
models:
  # Primary reasoning model
  primary:
    model_id: "model-id"               # Can use provider prefix (e.g., "anthropic/claude-3.5-sonnet")
    provider: "openrouter"             # Must be explicit (not auto-detected)
    
    # Fallback models for different providers
    provider_models:
      siliconflow: "qwen/qwen3-max"
      google: "gemini-2.5-flash"
    
    # Model-specific parameters (override provider defaults)
    parameters:
      temperature: 0.8
      max_tokens: 8192
  
  # Optional: separate embedding model configuration
  embedding:
    model_id: "embedding-model-id"
    provider: "siliconflow"
    provider_models:
      google: "gemini-embedding-001"
    parameters:
      dimensions: 2560

# Map environment variables to config paths for runtime overrides
env_overrides:
  # Syntax: ENV_VAR -> config.path.to.value
  AGENT_MODEL_ID: "models.primary.model_id"
  AGENT_PROVIDER: "models.primary.provider"
  AGENT_TEMPERATURE: "models.primary.parameters.temperature"
  AGENT_MAX_TOKENS: "models.primary.parameters.max_tokens"
  
  # Embedding configuration
  AGENT_EMBEDDER_MODEL: "models.embedding.model_id"
  AGENT_EMBEDDER_PROVIDER: "models.embedding.provider"

```

---

## Provider Auto-Detection and Fallback

### Auto-Detection

ValueCell automatically selects a primary provider based on available API keys:

**Priority order** (if multiple providers have API keys):

The selection logic is implemented in `python/valuecell/config/manager.py`:

1. OpenRouter
2. SiliconFlow
3. Google
4. OpenAI
5. OpenAI-Compatible
6. Azure
7. Other configured providers (including DashScope, DeepSeek, etc.)

Override this with an environment variable:

```bash
export PRIMARY_PROVIDER=siliconflow
```

Or disable auto-detection:

```bash
export AUTO_DETECT_PROVIDER=false
```

### Fallback Mechanism

If the primary provider fails, ValueCell automatically tries fallback providers.

**Fallback chain** (auto-populated from enabled providers):
- All providers with valid API keys, except the primary provider
- Stops at first successful model creation

To override fallback providers:

```bash
export FALLBACK_PROVIDERS=siliconflow,google
```

To disable fallback:

```bash
# In agent YAML
use_fallback: false
```

### Provider-Specific Model Mapping

When using fallback, agents can specify which model to use for each provider:

```yaml
# In agent configuration
models:
  primary:
    model_id: "anthropic/claude-haiku-4.5"
    provider: "openrouter"
    
    # If OpenRouter fails, use these models for fallback providers
    provider_models:
      siliconflow: "zai-org/GLM-4.6"      # Similar capability
      google: "gemini-2.5-flash"          # Fast and efficient
```

When fallback occurs:
1. Try OpenRouter with `anthropic/claude-haiku-4.5`
2. If fails, try SiliconFlow with `zai-org/GLM-4.6`
3. If fails, try Google with `gemini-2.5-flash`

---

## Environment Variables Reference

### Global Configuration

```bash
# Primary provider selection
PRIMARY_PROVIDER=openrouter

# Auto-detect provider from API keys (default: true)
AUTO_DETECT_PROVIDER=true

# Comma-separated fallback provider chain
FALLBACK_PROVIDERS=siliconflow,google

# Application environment
APP_ENVIRONMENT=production
```

### Provider Credentials

```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# SiliconFlow
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxx

# Google
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxx

# Azure OpenAI (if using Azure provider)
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://xxxxx.openai.azure.com/
OPENAI_API_VERSION=2024-10-21

# DashScope (Alibaba Cloud Qwen3 models)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
```

### Model Configuration

```bash
# Global model overrides
PLANNER_MODEL_ID=anthropic/claude-3.5-sonnet
EMBEDDER_MODEL_ID=openai/text-embedding-3-large

# Research Agent
RESEARCH_AGENT_MODEL_ID=google/gemini-2.5-flash
RESEARCH_AGENT_PROVIDER=openrouter
RESEARCH_AGENT_TEMPERATURE=0.8
RESEARCH_AGENT_MAX_TOKENS=8192
EMBEDDER_DIMENSION=3072

# Super Agent
SUPER_AGENT_MODEL_ID=anthropic/claude-haiku-4.5
SUPER_AGENT_PROVIDER=openrouter

# Auto Trading Agent
AUTO_TRADING_AGENT_MODEL_ID=model-id
AUTO_TRADING_AGENT_PROVIDER=openrouter
```

### Debugging

```bash
# Enable debug logging
AGENT_DEBUG_MODE=true
```

---

## Configuration Patterns

### Pattern 1: Multi-Model Setup with Fallback

**Use case**: High availability with cost optimization

```bash
# .env file
OPENROUTER_API_KEY=sk-or-v1-xxxxx        # Primary: access to many models
SILICONFLOW_API_KEY=sk-xxxxx             # Fallback: cost-effective
GOOGLE_API_KEY=AIzaSyD-xxxxx             # Second fallback: specialized
DASHSCOPE_API_KEY=sk-xxxxx               # DashScope: Qwen3 models (Chinese optimized)

# config.yaml
models:
  primary_provider: "openrouter"          # Primary (best models)
  # Fallback auto-populated as [siliconflow, google]
```

### Pattern 2: Specialized Models per Agent

**Use case**: Optimize each agent for its task

```yaml
# In research_agent.yaml
models:
  primary:
    provider: "openrouter"
    model_id: "anthropic/claude-3.5-sonnet"  # Best for research
    
  embedding:
    provider: "siliconflow"
    model_id: "Qwen/Qwen3-Embedding-4B"      # Best embeddings
```

### Pattern 3: Development vs Production

### OKX Trading

| Variable                 | Default | Description                                                        |
| ------------------------ | ------- | ------------------------------------------------------------------ |
| `OKX_NETWORK`            | `paper` | Choose `paper` for demo trading or `mainnet` for live environment. |
| `OKX_API_KEY`            | —       | OKX API key generated from the OKX console.                        |
| `OKX_API_SECRET`         | —       | API secret corresponding to the key.                               |
| `OKX_API_PASSPHRASE`     | —       | Passphrase set when creating the OKX API key.                      |
| `OKX_ALLOW_LIVE_TRADING` | `false` | Must be `true` before routing orders to the mainnet environment.   |
| `OKX_MARGIN_MODE`        | `cash`  | Trading mode passed to OKX (`cash`, `cross`, `isolated`).          |
| `OKX_USE_SERVER_TIME`    | `false` | Enable to sync with OKX server time for order stamping.            |

> [!IMPORTANT]
> Keep `OKX_ALLOW_LIVE_TRADING=false` until strategies are validated on the OKX paper environment. Treat API secrets as production credentials and store them in a secure vault.

## Troubleshooting
```bash
# .env.production  
OPENROUTER_API_KEY=sk-or-v1-prod-xxxxx
SILICONFLOW_API_KEY=sk-prod-xxxxx
APP_ENVIRONMENT=production
```

Then create `config.production.yaml` with production-specific settings.

### Pattern 4: Runtime Overrides

**Use case**: A/B testing different models without code changes

```bash
# Script to test different models
for model in "gpt-4o" "claude-3.5-sonnet" "gemini-2.5-flash"; do
    echo "Testing: $model"
    RESEARCH_AGENT_MODEL_ID="$model" python your_script.py
done
```

---

## For Developers

### Configuration System Architecture

The configuration system has three layers:

1. **Loader Layer** (`valuecell/config/loader.py`)
   - Reads YAML files
   - Resolves `${VAR}` placeholders
   - Applies environment variable overrides
   - Implements caching

2. **Manager Layer** (`valuecell/config/manager.py`)
   - High-level configuration access
   - Provider validation
   - Model factory integration
   - Fallback chain management

3. **Factory Layer** (`valuecell/adapters/models/factory.py`)
   - Creates actual model instances
   - Provider-specific implementations
   - Parameter merging
   - Error handling and fallback


### Creating a Model

```python
from valuecell.utils.model import get_model, get_model_for_agent

# Use default configuration
model = get_model("PLANNER_MODEL_ID")

# Override with kwargs
model = get_model("RESEARCH_AGENT_MODEL_ID", temperature=0.9, max_tokens=16384)

# Get agent-specific model
model = get_model_for_agent("research_agent", temperature=0.8)

# Use specific provider
from valuecell.utils.model import create_model_with_provider
model = create_model_with_provider("openrouter", "anthropic/claude-3.5-sonnet")
```

### Adding a New Provider

1. **Create provider YAML** (`configs/providers/my_provider.yaml`)
2. **Implement provider class** in `valuecell/adapters/models/factory.py`
3. **Register provider** in `ModelFactory._providers`
4. **Add to config.yaml** provider registry
5. **Add tests** for provider configuration

---

## Best Practices

1. **Set API Keys in .env**
   - Never commit API keys to version control
   - Use `.gitignore` to exclude `.env`
   - Use environment variables in CI/CD

2. **Use Provider Fallback**
   - Configure multiple providers for reliability
   - Specify `provider_models` in agents for consistent fallback
   - Test fallback behavior before deployment

3. **Monitor Configuration**
   - Log configuration selection decisions
   - Validate configuration on startup
   - Alert on missing API keys in production

4. **Version Your Configuration**
   - Keep agent configurations in version control
   - Document why specific models are chosen
   - Review configuration changes in code review

5. **Optimize Costs**
   - Use cheaper models for simple tasks
   - Use faster models for real-time applications
   - Monitor API usage and set spending limits

---

## Support

For configuration issues or questions:
- Ask on [Discord Community](https://discord.com/invite/84Kex3GGAh)
- Report bugs on [GitHub Issues](https://github.com/valuecell/valuecell/issues)
