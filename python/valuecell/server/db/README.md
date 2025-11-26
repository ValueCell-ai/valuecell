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
│   ├── agent.py        # Agent model
│   └── asset.py        # Asset model
└── README.md           # This document
```

## Database Configuration

Database configuration is defined in `valuecell/server/config/settings.py`:

- `VALUECELL_DATABASE_URL`: Database connection URL. Defaults to a SQLite file under the system application directory (same place as `.env`):
  - macOS: `sqlite:///~/Library/Application Support/ValueCell/valuecell.db`
  - Linux: `sqlite:///~/.config/valuecell/valuecell.db`
  - Windows: `sqlite:///%APPDATA%/ValueCell/valuecell.db`
- `DB_ECHO`: Whether to output SQL logs, defaults to `false`

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

### Asset Model (Asset)
The Asset model represents financial assets in the ValueCell system, including stocks, bonds, cryptocurrencies, and other investment instruments.

**Key fields**:
- `id`: Primary key (auto-increment)
- `symbol`: Unique asset symbol/ticker (e.g., "AAPL", "BTC-USD")
- `name`: Full name of the asset
- `description`: Detailed description of the asset
- `asset_type`: Type of asset (stock, bond, crypto, commodity, etc.)
- `sector`: Industry sector (for stocks)
- `current_price`: Current market price
- `is_active`: Whether the asset is active
- `asset_metadata`: Additional metadata (fundamental data, tags, etc.)
- `config`: Asset-specific configuration parameters
- `created_at`: Timestamp when the asset was created
- `updated_at`: Timestamp when the asset was last updated

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
3. **Create table structure**: Create agents and assets tables based on model definitions
4. **Initialize default data**:
   - **Agent data**: Insert default Agent records directly from code
     - Create three default agents: AIHedgeFundAgent, Sec13FundAgent, and TradingAgents
     - Support updating existing Agent configuration information
   - **Asset data**: Insert default Asset records for common financial instruments
     - Create default assets: AAPL, GOOGL, MSFT, SPY, BTC-USD
     - Support updating existing Asset information
5. **Verify initialization**: Confirm database connection and table structure are correct

### Default Records

The initialization script automatically creates default records directly in the code:

#### Default Agents

**Default agents created**:

1. **AIHedgeFundAgent**: AI-powered hedge fund analysis and trading agent
2. **Sec13FundAgent**: SEC 13F fund analysis and tracking agent  
3. **TradingAgents**: Multi-agent trading analysis system with market, sentiment, news and fundamentals analysis

#### Default Assets

**Default assets created**:

1. **AAPL**: Apple Inc. (Technology stock)
2. **GOOGL**: Alphabet Inc. Class A (Technology stock)
3. **MSFT**: Microsoft Corporation (Technology stock)
4. **SPY**: SPDR S&P 500 ETF Trust (Index ETF)
5. **BTC-USD**: Bitcoin (Cryptocurrency)

**Agent data structure example**:
```python
{
    "name": "TradingAgents",
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

**Asset data structure example**:
```python
{
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "asset_type": "stock",
    "sector": "Technology",
    "is_active": True,
    "metadata": {
        "market_cap": "large",
        "dividend_yield": 0.5,
        "beta": 1.2,
        "tags": ["blue-chip", "dividend", "growth"]
    }
}
```

## Usage in Code

### Getting Database Session

```python
from valuecell.server.db import get_db, Agent, Asset

# Using dependency injection in FastAPI routes
@app.get("/api/agents")
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).filter(Agent.enabled == True).all()

@app.get("/api/assets")
def get_assets(db: Session = Depends(get_db)):
    return db.query(Asset).filter(Asset.is_active == True).all()
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
    trading_agent = session.query(Agent).filter(Agent.name == "TradingAgents").first()
    
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
4. **Environment Variables**: Database connection can be customized through `VALUECELL_DATABASE_URL` environment variable

## Troubleshooting

### Common Issues

1. **Permission Error**: Ensure write permissions to database file directory
2. **Module Import Error**: Ensure running in correct Python environment
3. **Database Lock**: Ensure no other processes are using the database file

### Reset Database

If you need to completely reset the database:

```bash
# Delete existing database file (choose your OS path)
# macOS
rm -f "$HOME/Library/Application Support/ValueCell/valuecell.db"
# Linux
rm -f "$HOME/.config/valuecell/valuecell.db"
# Windows (PowerShell)
Remove-Item "$env:APPDATA\ValueCell\valuecell.db" -ErrorAction SilentlyContinue

# Re-initialize
python3 -m valuecell.server.db.init_db
```

Or use force re-initialization:

```bash
python3 -m valuecell.server.db.init_db --force
```