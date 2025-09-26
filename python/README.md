# ValueCell Python Package

ValueCell is a community-driven, multi-agent platform for financial applications.

## Installation

### Development Installation

Install the package in development mode with all dependencies (including testing tools like pytest, pytest-cov, and diff-cover):

```bash
uv sync --group dev
```

### Production Installation

```bash
uv sync
```

## Project Structure

- `valuecell/` - Main package
  - `adapters/` - External system adapters
  - `agents/` - Agent implementations
  - `config/` - Configuration and settings
  - `contrib/` - Community-contributed modules
  - `core/` - Core types, orchestration, and utilities
  - `server/` - API server components
  - `utils/` - Shared utility helpers
  - `tests/` - Test suite (module-level tests)
  
Top-level folders:

- `examples/` - End-to-end examples and notebooks
- `configs/` - Agent cards, locales, etc.
- `third_party/` - Third-party integrations (isolated)

### valuecell/core structure

Core contains the orchestration engine, types, and building blocks used by agents and the server.

- `valuecell/core/`
  - `agent/`
    - `card.py` - Agent capability/config card definitions
    - `client.py` - Client helpers for invoking agents
    - `connect.py` - Wiring utilities to connect agents and handlers
    - `decorator.py` - Decorators/executors for wrapping agent functions
    - `listener.py` - Event/listener primitives for agent events
    - `responses.py` - Response primitives and helpers
    - `tests/` - Unit tests for the agent module
  - `conversation/`
    - `conversation_store.py` - Conversation-level lifecycle and storage
    - `item_store.py` - Pluggable item storage backends (in-memory/SQLite)
    - `manager.py` - High-level conversation manager
    - `models.py` - Pydantic models for conversation data
    - `tests/` - Unit tests for conversation components
  - `coordinate/`
    - `models.py` - Types for coordination/planning
    - `orchestrator.py` - Orchestrates planning, tool calls, and streaming
    - `planner.py` - Planner implementation for step generation
    - `planner_prompts.py` - Prompt templates for planning
    - `response.py` - Unified response model for streaming and final results
    - `response_buffer.py` - Buffers and aggregates streaming responses
    - `response_router.py` - Routes responses to sinks/handlers
    - `tests/` - Unit and e2e tests for coordination
  - `task/`
    - `manager.py` - Manages task creation, lifecycle, and querying
    - `models.py` - Pydantic models for tasks
    - `tests/` - Unit tests for tasks
  - `types.py` - Shared core types and enums
  - `constants.py` - Core constants
  - `exceptions.py` - Core exception types

## Third Party Agents Integration

⚠️ **Caution**: Isolate third‑party libraries in separate virtual environments (uv, venv, virtualenv, or conda) to prevent dependency conflicts between components.

```bash
# ai-hedge-fund
cd third_party/ai-hedge-fund
echo "uv: $(which uv)"
echo "python: $(which python)"

uv venv --python 3.12 && uv sync && uv pip list
```

## Requirements

- Python >= 3.12
- Dependencies managed via `pyproject.toml`
