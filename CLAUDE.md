# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ValueCell

ValueCell is a community-driven, multi-agent platform for financial applications. It combines a Python FastAPI backend with a React/Tauri frontend to deliver AI-powered stock research, trading strategy automation, and portfolio management via a multi-agent orchestration system.

## Development Commands

### Backend (Python)

```bash
# Install dependencies
uv sync

# Run backend in dev mode
uv run python -m valuecell.server.main

# Tests
uv run pytest ./python                    # All tests
uv run pytest ./python/tests/test_foo.py  # Single file
uv run pytest -k "test_name"              # Single test by name

# Lint & format
make lint     # ruff check
make format   # ruff format + isort
```

### Frontend

```bash
cd frontend
bun install
bun run dev          # Dev server (port 1420)
bun run build        # Production build
bun run typecheck    # Type check (react-router typegen + tsc)
bun run lint         # Biome lint
bun run lint:fix     # Biome auto-fix
bun run format       # Biome format
```

### Docker (full stack)

```bash
docker compose up -d --build   # Start everything
docker compose logs -f         # Follow logs
```

### Quick start (full dev environment)

```bash
bash start.sh    # Linux/macOS — installs tools, syncs deps, starts both servers
```

## Architecture Overview

### Backend Layers

```
FastAPI (server/)
    └── Orchestrator (core/coordinate/orchestrator.py)
         ├── Super Agent (core/super_agent/) — triage: answer OR hand off to Planner
         ├── Planner (core/plan/planner.py) — converts intent → ExecutionPlan; triggers HITL
         ├── Task Executor (core/task/executor.py) — runs plan tasks via A2A protocol
         └── Event Router (core/event/) — maps A2A events → typed responses → UI stream
              └── Conversation Store (core/conversation/) — SQLite persistence
Agents (agents/)
    ├── research_agent/     — SEC EDGAR-based company analysis
    ├── prompt_strategy_agent/ — LLM-driven trading strategies
    ├── grid_agent/         — grid trading automation
    └── news_agent/         — news retrieval & scheduled delivery
Adapters (adapters/)
    ├── Yahoo Finance, AKShare, BaoStock — market data
    ├── CCXT — 40+ exchange integrations
    └── EDGAR — SEC filing retrieval
Storage
    ├── SQLite (aiosqlite/SQLAlchemy async) — conversations, tasks, watchlists
    └── LanceDB — vector embeddings
```

### Orchestration Flow

1. **Super Agent** — fast triage; either answers directly or enriches the query and hands off to Planner
2. **Planner** — produces a typed `ExecutionPlan`; detects missing params; blocks for Human-in-the-Loop (HITL) approval/clarification when needed
3. **Task Executor** — executes plan tasks asynchronously via Agent2Agent (A2A) protocol
4. **Event Router** — translates `TaskStatusUpdateEvent` → `BaseResponse` subtypes, annotates with stable `item_id`, streams to UI and persists

### Frontend Architecture

- **Framework**: React 19 + React Router 7 + Vite (rolldown)
- **Desktop**: Tauri 2 (cross-platform app wrapper)
- **State**: Zustand stores; TanStack React Query for server sync
- **Forms**: TanStack React Form + Zod
- **UI**: Radix UI headless components + Tailwind CSS 4 + shadcn
- **Charts**: ECharts + TradingView integration
- **i18n**: i18next (en, zh_CN, zh_TW, ja)
- Key entry points: `frontend/src/root.tsx` (routing), `frontend/src/app/agent/chat.tsx` (main chat UI)

### Configuration System (3-tier priority)

1. Environment variables (highest)
2. `.env` file
3. `python/configs/*.yaml` files (defaults: `config.yaml`, `providers/`, `agents/`, `agent_cards/`)

Copy `.env.example` to `.env` and set at least one LLM provider key (e.g. `OPENROUTER_API_KEY`).

## Code Conventions (from AGENTS.md)

- **Async-first**: all I/O must be async — use `httpx`, SQLAlchemy async, `anyio`
- **Type hints**: required on all public and internal APIs; prefer Pydantic models over `dict`
- **Imports**: avoid inline imports; use qualified imports for 3+ names from one module
- **Logging**: `loguru` with `{}` placeholders — `logger.info` for key events, `logger.warning` for recoverable errors, `logger.exception` only for unexpected errors
- **Error handling**: catch specific exceptions; max 2 nesting levels
- **Function size**: keep under 200 lines, max 10 parameters (prefer structs)
- **Runtime checks**: prefer Pydantic validation over `getattr`/`hasattr`
- **Python version**: 3.12+; package manager: `uv`; virtual env at `./python/.venv`
