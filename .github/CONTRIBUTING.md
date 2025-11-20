# Contributing to ValueCell

Thank you for your interest in contributing to ValueCell! We appreciate your help in making this multi-agent financial platform better. This guide will help you get started with contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md). Please read it before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Relevant logs** from `logs/{timestamp}/*.log`

### Suggesting Features

Feature requests are welcome! Please:

- **Check existing issues** to avoid duplicates
- **Describe the feature** and its use case clearly
- **Explain why** this feature would benefit ValueCell users

### Contributing Code

We welcome code contributions! See the [Development Setup](#development-setup) section below to get started.

***Reference Doc***

> Multi-agent system architecture: [CORE_ARCHITECTURE](../docs/CORE_ARCHITECTURE.md)  
> Configuration documentation: [CONFIGURATION_GUIDE](../docs/CONFIGURATION_GUIDE.md)  
> Agent development guide: [CONTRIBUTING_AN_AGENT](../docs/CONTRIBUTE_AN_AGENT.md)


## Development Setup

### Prerequisites

- **Python**: 3.12 or higher
- **[uv](https://docs.astral.sh/uv/)**: Fast Python package manager
- **[bun](https://bun.sh/)**: JavaScript/TypeScript toolkit (for frontend)

### Initial Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/valuecell.git
   cd valuecell
   ```

2. **First run**

   ```bash
   sh start.sh # MacOS, Linux
   .\start.ps1 # Windows
   ```
3. **Configuration**
   The project will automatically create a config file (.env) in your system ValueCell directory.
   You can configure your API key via the GUI settings tab.
   Refer to [Configuration Guide](../docs/CONFIGURATION_GUIDE.md) for details.

### Development Run
**Install backend dependencies:**

```bash
# Install pytest dependencies for testing

# Method 1: Using sync (recommended)
cd python
uv sync --extra dev

# Method 2: Using pip
uv pip install --editable ".[dev]"
```

**Install frontend dependencies:**

```bash
cd frontend
bun install
```

### Backend

For detailed information on building and contributing agents, see the [Agent Development Guide](../docs/CONTRIBUTING_AN_AGENT.md).

Quick start:

**Run the API server:**

```bash
cd python
python -m valuecell.server.main
```


### Code Style

### Backend and Agents

This section shows how to run the backend locally and build new agents.

#### Architecture at a glance

- API backend: `valuecell.server` (FastAPI/uvicorn). Entry: `valuecell.server.main`.
- Agents: under `valuecell.agents.<agent_name>` with a `__main__.py` for `python -m`.
- Core contracts: `valuecell.core.types` define response events and data shapes.
- Streaming helpers: `valuecell.core.agent.responses.streaming` for emitting events.

#### Create a new Agent

1. Subclass `BaseAgent` and implement `stream()`

```python
from typing import AsyncGenerator, Optional, Dict
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.core.agent.responses import streaming

class HelloAgent(BaseAgent):
   async def stream(
      self,
      query: str,
      conversation_id: str,
      task_id: str,
      dependencies: Optional[Dict] = None,
   ) -> AsyncGenerator[StreamResponse, None]:
      # Send a few chunks, then finish
      yield streaming.message_chunk("Thinking…")
      yield streaming.message_chunk(f"You said: {query}")
      yield streaming.done()
```

1. Wrap and serve (optional standalone service)

```python
# file: valuecell/agents/hello_agent/__main__.py
import asyncio
from valuecell.core.agent.decorator import create_wrapped_agent
from .core import HelloAgent

if __name__ == "__main__":
   agent = create_wrapped_agent(HelloAgent)
   asyncio.run(agent.serve())
```

Run it:

```bash
cd python
python -m valuecell.agents.hello_agent
```

> [!TIP]
> The wrapper standardizes transport and event emission so your agent integrates with the UI and logs consistently.

#### Add an Agent Card (required)

Agent Cards declare how your agent is discovered and served. Place a JSON file under:

`python/configs/agent_cards/`

The `name` must match your agent class name (e.g., `HelloAgent`). The `url` decides the host/port your wrapped agent will bind to.

Minimal example:

```json
{
  "name": "HelloAgent",
  "url": "http://localhost:10010",
  "description": "A minimal example agent that echoes input.",
  "capabilities": { "streaming": true, "push_notifications": false },
  "default_input_modes": ["text"],
  "default_output_modes": ["text"],
  "version": "1.0.0",
  "skills": [
   {
     "id": "echo",
     "name": "Echo",
     "description": "Echo user input back as streaming chunks.",
     "tags": ["example", "echo"]
   }
  ]
}
```

> [!TIP]
> Filename can be anything (e.g., `hello_agent.json`), but `name` must equal your agent class (used by `create_wrapped_agent`).
> Optional `enabled: false` will disable loading. Extra fields like `display_name` or `metadata` are ignored.
> Change the `url` port if it's occupied. The wrapper reads host/port from this URL when serving.
> If you see “No agent configuration found … in agent cards”, check the `name` and the JSON location.

#### Use models and tools inside an Agent

```python
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from valuecell.utils.model import get_model
from valuecell.core.agent.responses import streaming

class MyAgent(BaseAgent):
   def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self.inner = Agent(
         model=get_model("RESEARCH_AGENT_MODEL_ID"),
         tools=[...],  # your tool functions
         knowledge=...,  # optional: RAG knowledge base
         db=InMemoryDb(),
         debug_mode=True,
      )

   async def stream(self, query, conversation_id, task_id, dependencies=None):
      async for event in self.inner.arun(query, stream=True, stream_intermediate_steps=True):
         if event.event == "RunContent":
            yield streaming.message_chunk(event.content)
         elif event.event == "ToolCallStarted":
            yield streaming.tool_call_started(event.tool.tool_call_id, event.tool.tool_name)
         elif event.event == "ToolCallCompleted":
            yield streaming.tool_call_completed(event.tool.result, event.tool.tool_call_id, event.tool.tool_name)
      yield streaming.done()
```

> [!TIP]
> `get_model("RESEARCH_AGENT_MODEL_ID")` resolves the model from your `.env`. See the Config Guide for supported IDs.

#### Response Wrapper

Use `create_wrapped_agent(YourAgentClass)` to get a standardized server with:

- consistent event envelopes
- graceful startup/shutdown
- a minimal RPC layer for streaming

Example: see `valuecell/agents/research_agent/__main__.py`.

#### Event System (contracts)

Defined in `valuecell.core.types`:

- Stream events: `MESSAGE_CHUNK`, `TOOL_CALL_STARTED`, `TOOL_CALL_COMPLETED`, `REASONING*`
- Task lifecycle: `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_CANCELLED`
- System: `CONVERSATION_STARTED`, `THREAD_STARTED`, `PLAN_REQUIRE_USER_INPUT`, `DONE`

Emit events via `streaming.*` helpers and the UI will render progress, tool calls, and results in real time.

#### Debugging agent behavior

Use `AGENT_DEBUG_MODE` to enable verbose traces from agents and planners:

- Logs prompts, tool calls, intermediate steps, and provider response metadata
- Helpful to investigate planning decisions and tool routing during development

Enable in your `.env`:

```bash
AGENT_DEBUG_MODE=true
```

> [!CAUTION]
> Debug mode can log sensitive inputs/outputs and increases log volume/latency. Enable only in local/dev environments; keep it off in production.

### Code Style

#### Python

We use **Ruff** for linting and formatting, and **isort** for import sorting.

**Run formatting:**

```bash
make format
```

**Run linting:**

```bash
make lint
```

#### Frontend

We use **Biome** for linting and formatting.

**Run checks:**

```bash
cd frontend
bun run check:fix  # Auto-fix all issues
bun run format:fix # Auto lint code
```

**Key style rules:**

- Use TypeScript for type safety
- Follow React best practices
- Use functional components with hooks
- Maintain component modularity

## Testing

### Python Tests

**Run all tests:**

```bash
make test
```

**Run specific tests:**

```bash
uv run pytest ./python/valuecell/path/to/test.py
```

**Test requirements:**

- Write tests for new features
- Maintain or improve test coverage
- Ensure all tests pass before submitting PR

### Frontend Tests

Frontend testing guidelines are being established. Please ensure your code follows existing patterns.

## Commit Guidelines

We follow conventional commit messages for clarity and automation:

```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(agents): add European market support
fix(sec-agent): resolve SEC filing parsing error
docs: update installation instructions
```

## Pull Request Process

1. **Create a feature branch**
   
   Fork the project and use the `git clone` command to download it


   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**
   - Follow the code style guidelines
   - Write or update tests
   - Update documentation if needed

3. **Run checks locally**

   ```bash
   make format  # Format code
   make lint    # Check linting
   make test    # Run tests
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to your fork**

   ```bash
   git push origin feat/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the [ValueCell repository](https://github.com/ValueCell-ai/valuecell)
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template
   - Add appropriate labels
   - Request review

### PR Requirements

- ✅ All CI checks pass
- ✅ Code follows style guidelines
- ✅ Tests are included and passing
- ✅ Documentation is updated (if applicable)
- ✅ Commits follow commit guidelines
- ✅ PR description clearly explains changes

### Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged

## 🔥 ValueCell Dev Program

Build with us & get rewarded. Land 3 commits in the last month, and we will contact you via our official email (public@valuecell.ai).

You will get:

**💰 $100 Cash for API Keys and AI Coding Subscription**

**🚀 Become a core contributor and participate in the project's future profits**


## Questions?

If you have questions:

- 💬 Join our [Discord](https://discord.com/invite/84Kex3GGAh)
- 📧 Email us at [public@valuecell.ai](mailto:public@valuecell.ai)
- 🐛 Open an issue for bug reports

---

Thank you for contributing to ValueCell! 🚀🚀🚀

