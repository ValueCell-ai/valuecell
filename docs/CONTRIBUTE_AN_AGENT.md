# Contributing an Agent to ValueCell

This guide explains how to build, integrate, and contribute new agents to ValueCell's multi-agent financial platform.

## Kickstart 🚀

Want to quickly create a new agent? You can use an AI coding assistant like GitHub Copilot, Cursor, or other Agent Coders to bootstrap your agent automatically!

Simply share this guide with your AI assistant and ask:

> "Please create a HelloAgent following this guide."

The AI will read through this documentation and generate all necessary files:

- Agent module (`core.py`, `__main__.py`, `__init__.py`)
- Configuration files (YAML and JSON)
- Agent card registration (JSON)

This is the fastest way to get started and learn the agent structure hands-on!

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Create a New Agent](#create-a-new-agent)
- [Add an Agent Configuration](#add-an-agent-configuration-required)
- [Run Your Agent](#run-your-agent)
- [Use Models and Tools](#use-models-and-tools-inside-an-agent)
- [Event System](#event-system-contracts)
- [Launch Backend](#launch-backend)
- [Debugging Agent Behavior](#debugging-agent-behavior)

## Architecture Overview

Understanding the system architecture is crucial for building agents:

- **API backend**: `valuecell.server` (FastAPI/uvicorn). Entry: `valuecell.server.main`
- **Agents**: Located under `valuecell.agents.<agent_name>` with a `__main__.py` for `python -m` execution
- **Core contracts**: `valuecell.core.types` define response events and data shapes
- **Streaming helpers**: `valuecell.core.agent.stream` for emitting events

For more details, see

- [Core Architecture Documentation](./CORE_ARCHITECTURE.md)
- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [Main Contributing Guide](../.github/CONTRIBUTING.md).

## Create a New Agent

Creating a new agent involves three core steps:

1. **Implement the Agent Module** - Create the Python module with your agent's logic
2. **Add Agent Card** - Define metadata of agents
3. **Add Agent Configuration** - Configure models parameters

Let's walk through each step in detail.

### Step 1: Create Agent Directory Structure

Create a new directory for your agent under `python/valuecell/agents/`:

```bash
mkdir -p python/valuecell/agents/hello_agent
touch python/valuecell/agents/hello_agent/__init__.py
touch python/valuecell/agents/hello_agent/__main__.py
touch python/valuecell/agents/hello_agent/core.py
```

### Step 2: Implement Your Agent Logic

In `core.py`, subclass `BaseAgent` and implement the `stream()` method:

```python
# file: valuecell/agents/hello_agent/core.py
from typing import AsyncGenerator, Optional, Dict
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.core.agent import streaming

class HelloAgent(BaseAgent):
   async def stream(
      self,
      query: str,                    # User query content
      conversation_id: str,          # Conversation ID
      task_id: str,                  # Task ID
      dependencies: Optional[Dict] = None,  # Optional context (language, timezone, etc.)
   ) -> AsyncGenerator[StreamResponse, None]:
      """
      Process user queries and return streaming responses.
      
      Args:
          query: User query content
          conversation_id: Unique identifier for the conversation
          task_id: Unique identifier for the task
          dependencies: Optional dependencies containing language, timezone, and other context
      
      Yields:
          StreamResponse: Stream response containing content and completion status
      """
      # Send a few chunks, then finish
      yield streaming.message_chunk("Thinking…")
      yield streaming.message_chunk(f"You said: {query}")
      yield streaming.done()
```

**Agent Processing Flow Essentials:**

1. **Return Text Content**: Use `streaming.message_chunk()` to return text responses. You can send complete messages or split them into smaller chunks for better streaming UX.
2. **Signal Completion**: Always end with `streaming.done()` to indicate the agent has finished processing.

This simple flow enables real-time communication with the UI, displaying responses as they're generated.

### Step 3: Add Agent Entry Point

In `__main__.py`, wrap your agent for standalone execution. This file enables launching your agent with `uv run -m`:

```python
# file: valuecell/agents/hello_agent/__main__.py
import asyncio
from valuecell.core.agent import create_wrapped_agent
from .core import HelloAgent

if __name__ == "__main__":
   agent = create_wrapped_agent(HelloAgent)
   asyncio.run(agent.serve())
```

> [!IMPORTANT]
> Always place the wrap and serve logic in `__main__.py`. This pattern enables:
>
> - Consistent agent launching via `uv run -m valuecell.agents.your_agent`
> - Automatic discovery by the ValueCell backend server
> - Standardized transport and event emission

Run your agent:

```bash
cd python
uv run -m valuecell.agents.hello_agent
```

> [!TIP]
> The wrapper standardizes transport and event emission so your agent integrates with the UI and logs consistently.

## Add an Agent Configuration (Required)

Agent configurations define how your agent uses models, embeddings, and runtime parameters. Create a YAML file in `python/configs/agents/`.

### Create Configuration File

Create `python/configs/agents/hello_agent.yaml`:

```yaml
name: "Hello Agent"
enabled: true

# Model configuration
models:
  # Primary model
  primary:
    model_id: "anthropic/claude-haiku-4.5"
    provider: "openrouter"

# Environment variable overrides
env_overrides:
  HELLO_AGENT_MODEL_ID: "models.primary.model_id"
  HELLO_AGENT_PROVIDER: "models.primary.provider"
```

> [!TIP]
> The YAML filename should match your agent's module name (e.g., `hello_agent.yaml` for `hello_agent` module). This naming convention helps maintain consistency across the codebase.
> For detailed configuration options including embedding models, fallback providers, and advanced patterns, see [CONFIGURATION_GUIDE](./CONFIGURATION_GUIDE.md).

### Using Configuration in Your Agent

Load your agent's configuration using the config manager. The agent name passed to `get_model_for_agent()` must match the YAML filename (without the `.yaml` extension):

```python
from valuecell.utils.model import get_model_for_agent

class HelloAgent(BaseAgent):
   def __init__(self, **kwargs):
      super().__init__(**kwargs)
      # Automatically loads configuration from hello_agent.yaml
      # Agent name "hello_agent" must match the YAML filename
      self.model = get_model_for_agent("hello_agent")
   
   async def stream(self, query, conversation_id, task_id, dependencies=None):
      # Use your configured model
      response = await self.model.generate(query)
      yield streaming.message_chunk(response)
      yield streaming.done()
```

### Runtime Configuration Override

You can override configuration via environment variables:

```bash
# Override model at runtime
export HELLO_AGENT_MODEL_ID="anthropic/claude-3.5-sonnet"
export HELLO_AGENT_TEMPERATURE="0.9"

# Run your agent with overrides
uv run -m valuecell.agents.hello_agent
```

> [!TIP]
> For detailed configuration options including embedding models, fallback providers, and advanced patterns, see [CONFIGURATION_GUIDE](./CONFIGURATION_GUIDE.md).

## Add an Agent Card

Agent Cards declare how your agent is discovered and served. Place a JSON file under:

`python/configs/agent_cards/`

The `name` must match your agent class name (e.g., `HelloAgent`). The `url` decides the host/port your wrapped agent will bind to.

### Minimal Example

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
>
> - Filename can be anything (e.g., `hello_agent.json`), but `name` must equal your agent class (used by `create_wrapped_agent`)
> - Optional `enabled: false` will disable loading. Extra fields like `display_name` or `metadata` are ignored
> - Change the `url` port if it's occupied. The wrapper reads host/port from this URL when serving
> - If you see "No agent configuration found … in agent cards", check the `name` and the JSON location

## Run Your Agent

### Local Development

For local web development, simply start the backend server which will automatically load all agents:

```bash
# Start the full stack (frontend + backend with all agents)
bash start.sh

# Or start backend only
bash start.sh --no-frontend
```

The backend will automatically discover and initialize your agent based on the agent card configuration.

### Direct Agent Execution

You can also run your agent directly using Python module syntax:

```bash
cd python
uv run python -m valuecell.agents.hello_agent
```

### Client Application

For the packaged client application (Tauri):
1. The agent will be automatically included in the build
2. No additional registration is required
3. Test using workflow builds: `.github/workflows/mac_build.yml`

> [!TIP]
> Environment variables are loaded from system application directory:
> - **macOS**: `~/Library/Application Support/ValueCell/.env`
> - **Linux**: `~/.config/valuecell/.env`
> - **Windows**: `%APPDATA%\ValueCell\.env`
> 
> The `.env` file will be auto-created from `.env.example` on first run if it doesn't exist.
> Both local development and packaged client use the same location.

## Use Models and Tools Inside an Agent

Agents can use tools to extend their capabilities. Tools are Python functions that the agent can call during execution.

### Defining Tools

```python
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from valuecell.utils.model import get_model_for_agent

def search_stock_info(ticker: str) -> str:
    """
    Search for stock information by ticker symbol.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "GOOGL")
    
    Returns:
        Stock information as a string
    """
    # Your tool implementation here
    return f"Stock info for {ticker}"

def calculate_metrics(data: dict) -> dict:
    """
    Calculate financial metrics from stock data.
    
    Args:
        data: Dictionary containing financial data
    
    Returns:
        Dictionary with calculated metrics
    """
    # Your calculation logic here
    return {"pe_ratio": 25.5, "market_cap": "2.5T"}

class MyAgent(BaseAgent):
   def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self.inner = Agent(
         ...
         tools=[search_stock_info, calculate_metrics],  # Register your tools
         ...
      )
```

### Tool Best Practices

- **Clear docstrings**: Tools should have descriptive docstrings that explain their purpose and parameters
- **Type hints**: Use type hints for all parameters and return values
- **Error handling**: Implement proper error handling within tools
- **Focused functionality**: Each tool should do one thing well

> [!TIP]
> For more information, refer to [Tools - Agno](https://docs.agno.com/concepts/agents/tools).

## Event System (Contracts)

The event system enables real-time communication between agents and the UI. All events are defined in `valuecell.core.types`.

### Stream Events

Events for streaming agent responses:

- `MESSAGE_CHUNK` - A chunk of the agent's response message
- `TOOL_CALL_STARTED` - Agent begins executing a tool
- `TOOL_CALL_COMPLETED` - Tool execution finished
- `COMPONENT_GENERATOR` - Rich format components (charts, tables, reports, etc.)
- `DONE` - Indicating the streaming is finished

#### Component Generator Events

The `COMPONENT_GENERATOR` event allows agents to send rich UI components beyond plain text. This enables interactive visualizations, structured data displays, and custom widgets.

**Supported Component Types:**

- `report` - Research reports with formatted content
- `profile` - Company or stock profiles
- `filtered_line_chart` - Interactive line charts with data filtering
- `filtered_card_push_notification` - Notification cards with filter options
- `scheduled_task_controller` - UI for managing scheduled tasks
- `scheduled_task_result` - Display results of scheduled tasks

**Example: Emitting a Component**

```python
from valuecell.core.agent import streaming

# Create a line chart component
yield streaming.component_generator(
    component_type="filtered_line_chart",
    content={
        "title": "Stock Price Trends",
        "data": [
            ["Date", "AAPL", "GOOGL", "MSFT"],
            ["2025-01-01", 150.5, 2800.3, 380.2],
            ["2025-01-02", 152.1, 2815.7, 382.5],
        ],
        "create_time": "2025-01-15 10:30:00"
    }
)

# Create a report component
yield streaming.component_generator(
    component_type="report",
    content={
        "title": "Q4 2024 Financial Analysis",
        "data": "## Executive Summary\n\nRevenue increased by 15%...",
        "url": "https://example.com/reports/q4-2024",
        "create_time": "2025-01-15 10:30:00"
    }
)
```

> [!TIP]
> Component data structures are defined in `valuecell.core.types`. See `ReportComponentData`, `FilteredLineChartComponentData`, and other component payload classes for required fields.

### Emitting Events in Your Agent

Use the `streaming.*` helpers to emit events. Here's a practical example based on the Research Agent implementation:

```python
from agno.agent import Agent
from valuecell.core.agent import streaming
from valuecell.utils.model import get_model_for_agent

class MyAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inner = Agent(
            model=get_model_for_agent("my_agent"),
            tools=[...],  # your tool functions
            # ... other configuration
        )
    
    async def stream(self, query, conversation_id, task_id, dependencies=None):
        # Stream responses from the inner agent
        response_stream = self.inner.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,
            session_id=conversation_id,
        )
        
        # Process and forward events from the inner agent
        async for event in response_stream:
            if event.event == "RunContent":
                # Emit message chunks as they arrive
                yield streaming.message_chunk(event.content)
            
            elif event.event == "ToolCallStarted":
                # Notify UI that a tool is being called
                yield streaming.tool_call_started(
                    event.tool.tool_call_id, 
                    event.tool.tool_name
                )
            
            elif event.event == "ToolCallCompleted":
                # Send tool results back to UI
                yield streaming.tool_call_completed(
                    event.tool.result,
                    event.tool.tool_call_id,
                    event.tool.tool_name
                )
        
        # Signal completion
        yield streaming.done()
```

> [!TIP]
> Refer to [Running Agents - Agno](https://docs.agno.com/concepts/agents/running-agents) for details

> [!TIP]
> The UI automatically renders different event types appropriately - messages as text, tool calls with icons, etc. See the complete Research Agent implementation in `python/valuecell/agents/research_agent/core.py`.

## Launch Backend

### Run the API Server

From the `python/` folder:

```bash
cd python
python -m valuecell.server.main
```

### Run the Agent

Run the Hello Agent as a standalone service:

```bash
cd python
python -m valuecell.agents.hello_agent
```

> [!TIP]
> Set your environment first. At minimum, configure `SILICONFLOW_API_KEY` (and `OPENROUTER_API_KEY`) and `SEC_EMAIL`. See [CONFIGURATION_GUIDE](./CONFIGURATION_GUIDE.md).
> Optional: set `AGENT_DEBUG_MODE=true` to trace model behavior locally.

## Debugging Agent Behavior

Use `AGENT_DEBUG_MODE` to enable verbose traces from agents and planners:

- Logs prompts, tool calls, intermediate steps, and provider response metadata
- Helpful to investigate planning decisions and tool routing during development

Enable in your `.env`:

```bash
AGENT_DEBUG_MODE=true
```

> [!CAUTION]
> Debug mode can log sensitive inputs/outputs and increases log volume/latency. Enable only in local/dev environments; keep it off in production.

## Questions?

If you have questions:

- 💬 Join our [Discord](https://discord.com/invite/84Kex3GGAh)
- 📧 Email us at [public@valuecell.ai](mailto:public@valuecell.ai)
- 🐛 Open an issue for bug reports

---

Thank you for contributing to ValueCell! 🚀🚀🚀
