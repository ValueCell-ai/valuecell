# Configuration Guide

Configure ValueCell using environment variables in the `.env` file.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your settings, then restart the application
```

## Configuration Reference

### Agent settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_DEBUG_MODE` | false | Enables verbose debugging for agents and planners: logs prompts, tool calls, intermediate steps, and provider response metadata. Useful for diagnosing model behavior; disable in production. |

Typical use cases:

- Investigate unexpected model output or planning decisions
- Verify tool-call routing and inputs/outputs
- Capture detailed traces during local development

Enable it in your `.env`:

```bash
AGENT_DEBUG_MODE=true
```

> [!CAUTION]
> Debug mode may log raw prompts and tool payloads (potentially sensitive). It can also increase latency and log volume. Prefer enabling only on local/dev environments.

### Localization

| Variable | Default | Description |
|----------|---------|-------------|
| `LANG` | en-US | Supported: en_US, en_GB, zh-Hans, zh-Hant |
| `TIMEZONE` | America/New_York | IANA timezone format |

These values act as user preferences. Agents use them for response language, locale-aware formatting, and time conversions.

### Model Providers

**Required API Keys:**

- `OPENROUTER_API_KEY` - Get from [openrouter.ai](https://openrouter.ai/)
- `GOOGLE_API_KEY` - [Optional] Get from [Google AI Studio](https://aistudio.google.com/api-keys)

**Note**:

- OpenRouter API keys are the primary path to LLM access; you can pick models on OpenRouter.
- Gemini models are currently used only by the Planner and Research Agent. If `GOOGLE_API_KEY` is set, Planner and Research Agent will use Gemini native apis.

> [!IMPORTANT]
> On OpenRouter, the models `google/gemini-2.5-flash` and `google/gemini-2.5-pro` have compatibility issues at the moment. Prefer using a `GOOGLE_API_KEY` with Google AI Studio for Gemini, or select a stable alternative on OpenRouter.

**Model Selection:**

Role overview: the Planner is the central orchestrator (SuperAgent) that plans tasks and delegates to specialized agents (e.g., Research, Product).

| Variable | Default |
|----------|---------|
| `PLANNER_MODEL_ID` | google/gemini-2.5-flash |
| `RESEARCH_AGENT_MODEL_ID` | google/gemini-2.5-flash |
| `PRODUCT_MODEL_ID` | anthropic/claude-haiku-4.5 |

> [!CAUTION]
> Model ID formats differ by provider: OpenRouter uses `provider/model` (e.g., `openai/gpt-4o-mini`), while native APIs (e.g., Google) use provider-specific names (e.g., `gemini-2.5-flash`).

### Embedding and RAG

Embeddings power the local knowledge base (RAG) for retrieval. ValueCell stores vectors in LanceDB under `lancedb/`, enabling semantic search over your research notes.

> [!IMPORTANT]
> For now, we support OpenAI compatible embedding services. Some embedding models have fixed dimensions. Set `EMBEDDER_DIMENSION` to the model’s exact output size; mismatches will cause runtime errors.

| Variable | Required | Description |
|----------|----------|-------------|
| `EMBEDDER_API_KEY` | Yes | API key |
| `EMBEDDER_BASE_URL` | Yes | API base URL, (`https://api.openai.com/v1`, if not set) |
| `EMBEDDER_MODEL_ID` | Yes | Model identifier (text-embedding-3-small, if not set) |
| `EMBEDDER_DIMENSION` | Yes | Vector dimension (1568, if not set) |

Some useful exmaples:

```bash
# Siliconflow
EMBEDDER_BASE_URL=https://api.siliconflow.cn/v1/
EMBEDDER_MODEL_ID=Qwen/Qwen3-Embedding-4B
EMBEDDER_DIMENSION=2560
```

### Data Sources

**Required:**

- `SEC_EMAIL` - Your email (SEC API requirement). **Required if you use the Research Agent.**
- `FINNHUB_API_KEY` - Get free key from [finnhub.io/register](https://finnhub.io/register)

**Optional:**

- `XUEQIU_TOKEN` - From [xueqiu.com](https://xueqiu.com/) if Yahoo Finance is unstable

## Troubleshooting

**API Connection:**

- Verify `API_HOST` and `API_PORT`
- Check if port is in use
- Review firewall settings

**Model Providers:**

- Verify API keys are valid
- Check model IDs are correct
- Ensure sufficient credits

**Data Sources:**

- Set valid `SEC_EMAIL`
- Try `XUEQIU_TOKEN` if Yahoo Finance fails

## Security

- Never commit `.env` to version control
- Rotate API keys regularly
- Set file permissions: `chmod 600 .env`
- Use secrets management in production

## Resources

- [OpenRouter API](https://openrouter.ai/docs)
- [SEC EDGAR API](https://www.sec.gov/edgar/sec-api-documentation)
- [Finnhub API](https://finnhub.io/docs/api)
