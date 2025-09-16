# ValueCell Database Initialization

This directory contains database-related code for ValueCell Server, including model definitions, connection management, and initialization scripts.

## Directory Structure

```
db/
├── __init__.py          # Database package initialization
├── connection.py        # Database connection and session management
├── init_db.py          # Database initialization script
├── models/             # Database models
│   ├── __init__.py
│   ├── base.py         # Base model class
│   └── agent.py        # Agent model
└── README.md           # This document
```

## Database Configuration

Database configuration is defined in `valuecell/server/config/settings.py`:

- **DATABASE_URL**: Database connection URL, defaults to `sqlite:///./valuecell.db`
- **DB_ECHO**: Whether to output SQL logs, defaults to `false`

## Database Models

### Agent Model (Agent)
The Agent model stores information about all available AI agents in the ValueCell system:

**Basic Information**:
- `name`: Unique agent identifier
- `display_name`: Human-readable display name
- `description`: Detailed description of agent functionality and purpose
- `version`: Agent version number

**State Management**:
- `enabled`: Whether the agent is enabled
- `is_active`: Whether the agent is active and available

**Functionality**:
- `capabilities`: JSON format capability description (e.g., streaming, push notifications)
- `agent_metadata`: Additional metadata (author, tags, supported features, etc.)
- `config`: Agent-specific configuration parameters

**Timestamps**:
- `created_at`: Creation time
- `updated_at`: Update time

## Database Initialization

### Usage

1. **Basic initialization**:
   ```bash
   cd /path/to/valuecell/python
   python3 -m valuecell.server.db.init_db
   ```

2. **Force re-initialization**:
   ```bash
   python3 -m valuecell.server.db.init_db --force
   ```

3. **Verbose logging**:
   ```bash
   python3 -m valuecell.server.db.init_db --verbose
   ```

4. **Using standalone script**:
   ```bash
   python3 scripts/init_database.py
   ```

### Initialization Process

1. **Check database file**: Verify if SQLite database file exists
2. **Create database file**: Create new database file if it doesn't exist
3. **Create table structure**: Create agents table based on model definitions
4. **Initialize Agent data**:
   - Insert default Agent records directly from code
   - Create three default agents: AIHedgeFundAgent, Sec13FundAgent, and TradingAgentsAdapter
   - Support updating existing Agent configuration information
5. **Verify initialization**: Confirm database connection and table structure are correct

### Default Agent Records

The initialization script automatically creates default Agent records directly in the code:

**Default agents created**:

1. **AIHedgeFundAgent**: AI-powered hedge fund analysis and trading agent
2. **Sec13FundAgent**: SEC 13F fund analysis and tracking agent  
3. **TradingAgentsAdapter**: Multi-agent trading analysis system with market, sentiment, news and fundamentals analysis

**Agent data structure example**:
```python
{
    "name": "TradingAgentsAdapter",
    "display_name": "Trading Agents Adapter",
    "description": "TradingAgents - Multi-agent trading analysis system",
    "version": "1.0.0",
    "enabled": True,
    "is_active": True,
    "capabilities": {
        "streaming": True,
        "push_notifications": False
    },
    "metadata": {
        "version": "1.0.0",
        "author": "ValueCell Team",
        "tags": ["trading", "analysis", "multi-agent"],
        "supported_tickers": ["AAPL", "GOOGL", "MSFT"],
        "supported_analysts": ["market", "social", "news"]
    }
}
```

## Usage in Code

### Getting Database Session

```python
from valuecell.server.db import get_db, Agent

# Using dependency injection in FastAPI routes
@app.get("/api/agents")
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).filter(Agent.enabled == True).all()
```

### Direct Database Manager Usage

```python
from valuecell.server.db import get_database_manager, Agent

db_manager = get_database_manager()
session = db_manager.get_session()

try:
    # Get all enabled agents
    agents = session.query(Agent).filter(Agent.enabled == True).all()
    
    # Get specific agent
    trading_agent = session.query(Agent).filter(Agent.name == "TradingAgentsAdapter").first()
    
    # Update agent status
    if trading_agent:
        trading_agent.is_active = True
        session.commit()
finally:
    session.close()
```

### Programmatic Initialization

```python
from valuecell.server.db import init_database

# Initialize database
success = init_database(force=False)
if success:
    print("Database initialization successful")
else:
    print("Database initialization failed")
```

## Important Notes

1. **Password Security**: Default admin user password is a placeholder and should be replaced with proper hashed password in production environment
2. **Database Backup**: SQLite database file should be backed up regularly
3. **Permission Management**: Ensure database file has appropriate filesystem permissions
4. **Environment Variables**: Database connection can be customized through `DATABASE_URL` environment variable

## Troubleshooting

### Common Issues

1. **Permission Error**: Ensure write permissions to database file directory
2. **Module Import Error**: Ensure running in correct Python environment
3. **Database Lock**: Ensure no other processes are using the database file

### Reset Database

If you need to completely reset the database:

```bash
# Delete existing database file
rm valuecell.db

# Re-initialize
python3 -m valuecell.server.db.init_db
```

Or use force re-initialization:

```bash
python3 -m valuecell.server.db.init_db --force
```