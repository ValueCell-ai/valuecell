# ValueCell Agent System

The ValueCell Agent System is a distributed intelligent agent framework based on the Agent-to-Agent (A2A) protocol, providing a clean decorator interface and powerful connection management capabilities.

## Core Features

- 🎯 **Simple Decorator**: Easily create Agents using the `@serve` decorator
- 🔄 **Streaming Response**: Support for real-time streaming data processing
- 🌐 **Distributed Architecture**: Support for both local and remote Agent connections
- 📡 **Push Notifications**: Optional push notification functionality
- 🔧 **Flexible Configuration**: Support for automatic port allocation and custom configuration
- 📋 **Agent Registry**: Unified management of all Agent instances

## Quick Start

### 1. Create a Simple Agent

```python
from valuecell.core.agent.decorator import serve

@serve(push_notifications=True)
class CalculatorAgent:
    """An agent that can perform basic math calculations"""
    
    def __init__(self):
        self.agent_name = "CalculatorAgent"
    
    async def stream(self, query, session_id, task_id):
        """Process math queries"""
        yield {"is_task_complete": False, "content": f"🧮 Calculating: {query}"}
        
        # Execute calculation logic
        try:
            if any(op in query for op in ["+", "-", "*", "/", "(", ")"]):
                result = eval(query)  # Note: Use safe parsing in production
                yield {"is_task_complete": True, "content": f"✅ Result: {result}"}
            else:
                yield {
                    "is_task_complete": True, 
                    "content": "❓ Please enter a math expression, e.g., '2 + 3'"
                }
        except Exception as e:
            yield {
                "is_task_complete": True,
                "content": f"❌ Calculation error: {str(e)}"
            }
```

### 2. Use RemoteConnections to manage Agents

```python
import asyncio
from valuecell.core.agent.connect import RemoteConnections

async def main():
    # Create connection manager
    connections = RemoteConnections()
    
    # List all available Agents
    available = connections.list_available_agents()
    print(f"Available Agents: {available}")
    
    # Start Agent
    calc_url = await connections.start_agent("CalculatorAgent")
    print(f"Calculator Agent started at: {calc_url}")
    
    # Get client and send message
    client = await connections.get_client("CalculatorAgent")
    task, event = await client.send_message("What is 15 + 27?")
    print(f"Calculation result: {task.status}")
    
    # Clean up resources
    await connections.stop_all()

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Components

### 1. @serve Decorator

The `@serve` decorator is the core tool for creating Agents, providing the following parameters:

```python
@serve(
    host="localhost",          # Service host
    port=9100,                 # Service port (optional, auto-allocated)
    streaming=True,            # Whether to support streaming response
    push_notifications=False,  # Whether to enable push notifications
    description="Description",  # Agent description
    version="1.0.0",          # Agent version
    skills=[]                  # Agent skills list
)
```

### 2. RemoteConnections Class

`RemoteConnections` is the core class for Agent connection management, providing the following functionality:

#### Basic Operations

```python
connections = RemoteConnections()

# List all available Agents (local + remote)
available_agents = connections.list_available_agents()

# List running Agents
running_agents = connections.list_running_agents()

# Start Agent
agent_url = await connections.start_agent("AgentName")

# Get Agent client
client = await connections.get_client("AgentName")

# Stop specific Agent
await connections.stop_agent("AgentName")

# Stop all Agents
await connections.stop_all()
```

#### Remote Agent Support

```python
# List remote Agents
remote_agents = connections.list_remote_agents()

# Get remote Agent configuration
card_data = connections.get_remote_agent_card("RemoteAgentName")

# Get Agent information
agent_info = connections.get_agent_info("AgentName")
```

### 3. AgentClient Class

`AgentClient` provides the interface for communicating with Agents:

```python
client = AgentClient("http://localhost:9100/")

# Send message (non-streaming)
task, event = await client.send_message("Hello Agent")

# Send message (streaming)
async for response in await client.send_message("Stream query", streaming=True):
    print(f"Streaming response: {response}")

# Get Agent card information
card = await client.get_agent_card()

# Close connection
await client.close()
```

### 4. Agent Registry

`AgentRegistry` manages all registered Agents:

```python
from valuecell.core.agent.registry import AgentRegistry

# List all registered Agents
agents = AgentRegistry.list_agents()

# Get specific Agent class
agent_class = AgentRegistry.get_agent("AgentName")

# Get registry detailed information
info = AgentRegistry.get_registry_info()
```

## Complete Examples

### Example 1: Multi-Agent System

```python
import asyncio
import logging
from valuecell.core.agent.decorator import serve
from valuecell.core.agent.connect import RemoteConnections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@serve(push_notifications=True)
class CalculatorAgent:
    async def stream(self, query, session_id, task_id):
        yield {"is_task_complete": False, "content": f"🧮 Calculating: {query}"}
        await asyncio.sleep(0.5)
        yield {"is_task_complete": True, "content": "✅ Calculation complete"}

@serve(port=9101, push_notifications=True)
class WeatherAgent:
    async def stream(self, query, session_id, task_id):
        yield {"is_task_complete": False, "content": f"🌤️ Checking weather: {query}"}
        await asyncio.sleep(0.8)
        yield {"is_task_complete": True, "content": "☀️ Today's weather: Sunny, 22°C"}

async def demo():
    connections = RemoteConnections()
    
    try:
        # Start multiple Agents
        calc_url = await connections.start_agent("CalculatorAgent")
        weather_url = await connections.start_agent("WeatherAgent")
        
        logger.info(f"Calculator Agent: {calc_url}")
        logger.info(f"Weather Agent: {weather_url}")
        
        # Wait for Agents to start
        await asyncio.sleep(2)
        
        # Test Calculator Agent
        calc_client = await connections.get_client("CalculatorAgent")
        task, _ = await calc_client.send_message("2 + 3")
        logger.info(f"Calculator result: {task.status}")
        
        # Test Weather Agent
        weather_client = await connections.get_client("WeatherAgent")
        task, _ = await weather_client.send_message("How's the weather in Beijing?")
        logger.info(f"Weather result: {task.status}")
        
        await asyncio.sleep(5)
        
    finally:
        await connections.stop_all()

if __name__ == "__main__":
    asyncio.run(demo())
```

### Example 2: Remote Agent Connection

```python
import asyncio
import logging
from valuecell.core.agent.connect import RemoteConnections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def remote_demo():
    connections = RemoteConnections()
    
    # List all available Agents (including remote ones)
    available_agents = connections.list_available_agents()
    logger.info(f"Available Agents: {available_agents}")
    
    # List remote Agents
    remote_agents = connections.list_remote_agents()
    logger.info(f"Remote Agents: {remote_agents}")
    
    # Connect to remote Agent (if any)
    if remote_agents:
        agent_name = remote_agents[0]
        try:
            agent_url = await connections.start_agent(agent_name)
            logger.info(f"Successfully connected to remote Agent {agent_name}: {agent_url}")
            
            # Get client and send message
            client = await connections.get_client(agent_name)
            
            # Stream process message
            async for response in await client.send_message(
                "Analyze Apple stock", 
                streaming=True
            ):
                logger.info(f"Remote response: {response}")
                
        except Exception as e:
            logger.error(f"Failed to connect to remote Agent {agent_name}: {e}")

if __name__ == "__main__":
    asyncio.run(remote_demo())
```

## Agent Development Guide

### 1. Agent Interface Implementation

All Agents must implement the `stream` method:

```python
async def stream(self, query, session_id, task_id):
    """
    Process user queries and return streaming responses
    
    Args:
        query: User query content
        session_id: Session ID
        task_id: Task ID
        
    Yields:
        dict: Dictionary containing 'content' and 'is_task_complete'
    """
    pass
```

### 2. Response Format

Each response should be a dictionary containing the following fields:

```python
{
    "content": "Response content",        # Required: Text content of the response
    "is_task_complete": False            # Required: Whether the task is complete
}
```

### 3. Error Handling

It's recommended to add appropriate error handling in Agents:

```python
async def stream(self, query, session_id, task_id):
    try:
        # Processing logic
        yield {"is_task_complete": False, "content": "Processing..."}
        # ... business logic ...
        yield {"is_task_complete": True, "content": "Complete"}
    except Exception as e:
        yield {
            "is_task_complete": True,
            "content": f"❌ Processing error: {str(e)}"
        }
```

### 4. Asynchronous Operations

Agents can perform asynchronous operations internally:

```python
async def stream(self, query, session_id, task_id):
    yield {"is_task_complete": False, "content": "Starting process..."}
    
    # Asynchronous wait
    await asyncio.sleep(1)
    
    yield {"is_task_complete": False, "content": "Intermediate step..."}
    
    # More asynchronous operations
    result = await some_async_function()
    
    yield {"is_task_complete": True, "content": f"Complete: {result}"}
```

## Configuration

### Remote Agent Configuration

Create JSON configuration files in the `python/configs/agent_cards/` directory:

```json
{
    "name": "Hedge Fund Agent",
    "url": "http://localhost:8080/",
    "description": "Professional hedge fund analysis Agent",
    "version": "1.0.0",
    "capabilities": {
        "streaming": true,
        "push_notifications": true
    }
}
```

### Environment Variables

Configuration via environment variables:

```bash
export VALUECELL_AGENT_HOST=localhost
export VALUECELL_AGENT_PORT_RANGE_START=9100
export VALUECELL_AGENT_PORT_RANGE_END=9200
```

## Testing

Run core functionality tests:

```bash
cd python
python -m pytest valuecell/core/agent/tests/ -v
```

Run complete end-to-end tests:

```bash
python valuecell/examples/core_e2e_demo.py
```

Test remote Agent connections:

```bash
python valuecell/examples/core_remote_agent_demo.py
```

## Logging

The system uses Python's standard logging library. Recommended configuration:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
```

## Performance Considerations

1. **Port Management**: The system automatically allocates available ports to avoid conflicts
2. **Connection Reuse**: RemoteConnections manages connection pools to avoid duplicate connections
3. **Asynchronous Processing**: Full asynchronous architecture supporting high concurrency
4. **Streaming Response**: Reduces memory usage and improves response speed
5. **Error Recovery**: Built-in error handling and recovery mechanisms

## Troubleshooting

### Common Issues

1. **Port Conflicts**

   ```bash
   Solution: Use automatic port allocation or specify different ports
   ```

2. **Agent Not Registered**

   ```python
   # Ensure Agent class is imported
   from your_module import YourAgent
   ```

3. **Connection Failure**

   ```python
   # Check if Agent is running
   running = connections.list_running_agents()
   print(running)
   ```

4. **Remote Agent Connection Issues**

   ```bash
   Check configuration file format and network connectivity
   ```

### Debug Mode

Enable verbose logging:

```python
logging.getLogger("valuecell.core.agent").setLevel(logging.DEBUG)
```
