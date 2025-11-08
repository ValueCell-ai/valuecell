# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ValueCell is a community-driven, multi-agent platform for financial applications. It provides a team of AI investment agents for stock selection, research, tracking, and trading. The project uses Python 3.12+ for backend/agents and React/TypeScript (React Router v7) for the frontend.

## Common Commands

### Running the Application

```bash
# Start entire application (frontend + backend + agents)
bash start.sh

# Windows
.\start.ps1

# Start only backend
bash start.sh --no-frontend

# Start only frontend
bash start.sh --no-backend
```

The application will be available at http://localhost:1420

### Development Setup

```bash
# First-time setup: prepare all environments (main + third-party)
cd python
bash scripts/prepare_envs.sh

# Install main Python dependencies
cd python
uv sync --group dev

# Install frontend dependencies
cd frontend
bun install
```

### Running Individual Agents

```bash
# Launch specific agents via the launcher
cd python
uv run --env-file ../.env --with questionary scripts/launch.py

# Or run agents directly
uv run --env-file ../.env -m valuecell.agents.research_agent
uv run --env-file ../.env -m valuecell.agents.auto_trading_agent
uv run --env-file ../.env -m valuecell.agents.news_agent
uv run --env-file ../.env -m valuecell.agents.strategy_agent
```

### Testing and Code Quality

```bash
# Run tests
make test
# or
uv run pytest ./python

# Format code
make format
# or
ruff format --config ./python/pyproject.toml ./python/
uv run --directory ./python isort .

# Lint code
make lint
# or
ruff check --config ./python/pyproject.toml ./python/

# Frontend linting and formatting
cd frontend
bun run lint
bun run format
bun run check        # Run biome check
bun run check:fix    # Auto-fix issues
```

### Database Management

```bash
# Initialize database
cd python
uv run valuecell/server/db/init_db.py

# If you encounter database compatibility issues, delete and restart:
rm -rf lancedb/ valuecell.db .knowledgebase/
```

## Architecture Overview

### High-Level Structure

```
valuecell/
├── frontend/          # React Router v7 + TypeScript frontend
├── python/
│   ├── valuecell/     # Main Python package
│   ├── configs/       # YAML configuration files
│   ├── scripts/       # Utility scripts (launch, prepare_envs)
│   └── third_party/   # Third-party agent integrations
├── docs/              # Documentation
└── start.sh           # Application launcher
```

### Python Package Structure

```
python/valuecell/
├── core/              # Core orchestration and coordination
│   ├── agent/         # Agent decorator, listener, client
│   ├── conversation/  # Conversation management & stores
│   ├── coordinate/    # Main orchestrator
│   ├── super_agent/   # Triage agent (ANSWER vs HANDOFF)
│   ├── plan/          # Planner with HITL support
│   ├── task/          # Task execution
│   └── event/         # Event response routing & buffering
├── agents/            # Concrete agent implementations
│   ├── research_agent/
│   ├── auto_trading_agent/
│   ├── news_agent/
│   └── strategy_agent/
├── server/            # FastAPI backend
│   ├── api/           # API routes
│   ├── db/            # Database models and stores
│   └── services/      # Business logic
├── adapters/          # External integrations
│   ├── models/        # LLM provider factory
│   ├── assets/        # Asset data providers
│   └── db/            # Database adapters
├── config/            # Configuration management
└── utils/             # Shared utilities
```

### Configuration System

ValueCell uses a three-tier configuration system:

1. **Environment Variables** (highest priority) - Set in `.env` file
2. **YAML Files** - In `python/configs/` directory
   - `config.yaml` - Global defaults
   - `providers/` - LLM provider configs (OpenRouter, SiliconFlow, Google, etc.)
   - `agents/` - Agent-specific configurations
   - `agent_cards/` - UI metadata for agents
3. **Code Defaults** (lowest priority)

**Key configuration files:**
- `.env` - API keys and runtime settings (copy from `.env.example`)
- `python/configs/config.yaml` - Primary provider, model defaults
- `python/configs/agents/*.yaml` - Per-agent model and parameter settings
- `python/configs/providers/*.yaml` - Provider connection details

See `docs/CONFIGURATION_GUIDE.md` for detailed configuration documentation.

## Core Orchestration Flow

The system follows an **async, re-entrant orchestrator pattern** with streaming responses:

1. **User Input** → `AgentOrchestrator.process_user_input()`
2. **Super Agent Triage** - Quick analysis to decide:
   - `ANSWER` - Respond directly for simple queries
   - `HANDOFF_TO_PLANNER` - Complex requests needing planning
3. **Planning (with HITL)** - `PlanService` creates execution plan
   - Can pause for human confirmation via `UserInputRequest`
   - Resumes after user feedback
4. **Task Execution** - `TaskExecutor` runs plan steps
   - Calls remote agents via A2A (Agent-to-Agent) protocol
   - Streams task status events back
5. **Response Pipeline**:
   - `ResponseRouter` - Maps A2A events to typed `BaseResponse` objects
   - `ResponseBuffer` - Annotates with stable item IDs, aggregates partials
   - Persists to `ConversationStore` (SQLite or in-memory)
   - Streams to UI

**Key insight:** The orchestrator decouples producers/consumers, allowing long-running tasks to continue even if the client disconnects.

## Agent Development

### Creating a New Agent

1. Create agent directory: `python/valuecell/agents/my_agent/`
2. Add agent configuration: `python/configs/agents/my_agent.yaml`
3. Implement agent using the `agno` framework (see existing agents as examples)
4. Wrap with `@create_wrapped_agent` decorator for A2A integration
5. Register in `scripts/launch.py` for standalone execution
6. Add agent card metadata in `python/configs/agent_cards/my_agent.yaml`

See `docs/CONTRIBUTE_AN_AGENT.md` for detailed guide.

### Agent Framework

Agents use the **Agno** framework (`agno` package), which provides:
- Multi-modal LLM integration
- Tool/function calling
- Knowledge base (RAG) with LanceDB
- Memory management
- Async streaming

## Model Provider System

ValueCell supports multiple LLM providers with automatic fallback:

**Supported providers:**
- OpenRouter (recommended for multi-model access)
- SiliconFlow (cost-effective, Chinese models)
- Google (Gemini)
- Azure OpenAI
- OpenAI
- Custom OpenAI-compatible endpoints

**Auto-detection priority:**
1. OpenRouter
2. SiliconFlow
3. Google
4. Others

**Fallback mechanism:** If primary provider fails, automatically tries other configured providers with appropriate model mappings (defined in agent YAML `provider_models` field).

**Factory pattern:** `valuecell/adapters/models/factory.py` handles model instantiation with provider-specific implementations.

## Third-Party Agent Integration

The project integrates third-party agents in isolated environments:

- `python/third_party/ai-hedge-fund/` - AI Hedge Fund agents (various analyst personas)
- `python/third_party/TradingAgents/` - Trading strategy agents

**Important:** Each third-party directory has its own `pyproject.toml` and virtual environment to prevent dependency conflicts. Use `scripts/prepare_envs.sh` to set up all environments.

## Testing

Tests use `pytest` with async support (`pytest-asyncio`):

```bash
# Run all tests
uv run pytest ./python

# Run specific test file
uv run pytest ./python/valuecell/core/plan/tests/test_planner.py

# Run with coverage
uv run pytest --cov=valuecell --cov-report=html ./python
```

**Test structure mirrors source structure:**
- Tests live in `tests/` subdirectories alongside the code they test
- Example: `valuecell/core/plan/tests/test_planner.py`

## Frontend Development

```bash
cd frontend

# Development server (with HMR)
bun run dev

# Type checking
bun run typecheck

# Build for production
bun run build

# Preview production build
bun run start
```

**Tech stack:**
- React Router v7 (file-based routing)
- React 19
- TypeScript
- Tailwind CSS v4
- Radix UI components
- Zustand for state management
- TanStack Query for data fetching
- Biome for linting/formatting

**Key directories:**
- `frontend/src/routes/` - File-based routing
- `frontend/src/components/` - Reusable components
- `frontend/src/api/` - API client
- `frontend/src/store/` - Zustand stores
- `frontend/src/hooks/` - Custom React hooks

## API Development

Backend uses **FastAPI** with:
- A2A (Agent-to-Agent) protocol via `a2a-sdk`
- SQLAlchemy with SQLite/async support
- Uvicorn ASGI server

**Key files:**
- `python/valuecell/server/main.py` - Entry point
- `python/valuecell/server/api/app.py` - FastAPI app factory
- `python/valuecell/server/api/` - Route handlers
- `python/valuecell/server/services/` - Business logic

**Default API settings:**
- Host: `localhost`
- Port: `8000`
- Debug mode: Controlled by `API_DEBUG` env var

## OKX Trading Integration

For live/paper crypto trading via OKX:

**Environment variables:**
```bash
AUTO_TRADING_EXCHANGE=okx
OKX_NETWORK=paper              # Use 'mainnet' for live trading
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_API_PASSPHRASE=...
OKX_ALLOW_LIVE_TRADING=false   # Must be true for mainnet
OKX_MARGIN_MODE=cash           # or cross/isolated
```

**Safety:** Keep `OKX_ALLOW_LIVE_TRADING=false` until strategies are validated on paper. See `docs/OKX_SETUP.md` for details.

## Logging

Logs are written to `logs/{timestamp}/` directory:
- `{AgentName}.log` - Per-agent logs
- `backend.log` - Backend server logs

The `launch.py` script automatically creates timestamped log directories and redirects output.

## Important Notes

- **Python 3.12+ required** - The project uses modern Python features
- **Use `uv` for Python** - Fast dependency management (auto-installed by `start.sh`)
- **Use `bun` for frontend** - Fast JavaScript runtime and package manager
- **Third-party isolation** - Third-party agents run in separate virtual environments
- **Configuration over code** - Prefer YAML configs for agent/model settings
- **Async-first** - Most core code is async; use `await` appropriately
- **A2A protocol** - Agents communicate via standardized Agent-to-Agent protocol
- **Streaming responses** - UI receives incremental updates during long-running tasks
- **HITL support** - Planner can pause for human input and resume

## Common Troubleshooting

**Database compatibility issues:**
```bash
rm -rf lancedb/ valuecell.db .knowledgebase/
cd python && uv run valuecell/server/db/init_db.py
```

**Missing environment variables:**
- Ensure `.env` exists (copy from `.env.example`)
- Configure at least one LLM provider API key

**Dependency conflicts:**
- Third-party agents use isolated environments
- Run `bash scripts/prepare_envs.sh` to reset all environments

**Frontend build errors:**
- Ensure bun is installed: `brew install bun` (macOS)
- Clear cache: `rm -rf frontend/node_modules frontend/.react-router`
