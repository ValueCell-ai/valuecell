# Developer Guide

This guide shows how to run the backend and build new agents in ValueCell.

## Launch

Run the API server (from the `python/` folder):

```bash
cd python
python -m valuecell.server.main
```

For example, run the built‑in Research Agent as a standalone service:

```bash
cd python
python -m valuecell.agents.research_agent
```

> [!TIP]
> Set your environment first. At minimum, configure `OPENROUTER_API_KEY` (or `GOOGLE_API_KEY`) and `SEC_EMAIL`. See `docs/CONFIGURATION_GUIDE.md`.
> Optional: set `AGENT_DEBUG_MODE=true` to trace model behavior locally.

## Architecture at a glance

- API backend: `valuecell.server` (FastAPI/uvicorn). Entry: `valuecell.server.main`.
- Agents: live under `valuecell.agents.<agent_name>` with a `__main__.py` for `python -m`.
- Core contracts: `valuecell.core.types` defines response events and data shapes.
- Streaming helpers: `valuecell.core.agent.responses.streaming` for emitting events.

## Create a new Agent

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

## Add an Agent Card (required)

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

## Use models and tools inside an Agent

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

## Response Wrapper

Use `create_wrapped_agent(YourAgentClass)` to get a standardized server with:

- consistent event envelopes
- graceful startup/shutdown
- a minimal RPC layer for streaming

Example: see `valuecell/agents/research_agent/__main__.py`.

## Event System (contracts)

Defined in `valuecell.core.types`:

- Stream events: `MESSAGE_CHUNK`, `TOOL_CALL_STARTED`, `TOOL_CALL_COMPLETED`, `REASONING*`
- Task lifecycle: `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_CANCELLED`
- System: `CONVERSATION_STARTED`, `THREAD_STARTED`, `PLAN_REQUIRE_USER_INPUT`, `DONE`

Emit events via `streaming.*` helpers and the UI will render progress, tool calls, and results in real time.

## Debugging model behavior

Use `AGENT_DEBUG_MODE` to enable verbose traces from agents and planners:

- Logs prompts, tool calls, intermediate steps, and provider response metadata
- Helpful to investigate planning decisions and tool routing during development

Enable in your `.env`:

```bash
AGENT_DEBUG_MODE=true
```

> [!CAUTION]
> Debug mode can log sensitive inputs/outputs and increases log volume/latency. Enable only in local/dev environments; keep it off in production.

## Code Style

- We use `ruff` to format and lint codes.
- Logs: we use `loguru`; prefer structured, concise logs.
- Keep examples small. Add features iteratively.
