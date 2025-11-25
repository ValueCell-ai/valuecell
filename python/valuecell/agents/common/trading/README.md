# Trading Agent Framework

This document describes the common trading agent framework: a flexible, composable architecture for building LLM-driven trading strategies with clean separation of concerns and extensible components.

## Architecture Overview

The framework provides a base class (`BaseStrategyAgent`) that handles lifecycle management, streaming, and persistence, while allowing users to customize decision logic and feature computation through well-defined extension points.

**Key Principles:**

- **Separation of Concerns**: Data fetching, feature computation, decision making, execution, and history tracking are independent modules
- **Extensibility**: Override specific components without rewriting the entire pipeline
- **Type Safety**: Pydantic models ensure data contracts across boundaries
- **Async-First**: Built on asyncio for efficient I/O and concurrent operations
- **Auditable**: Each decision cycle has a unique `compose_id` for tracing

## Module Layout

```text
common/trading/
├── base_agent.py          # BaseStrategyAgent abstract class
├── models.py              # Pydantic DTOs and enums
├── constants.py           # Default configuration values
├── utils.py               # Shared utilities
├── _internal/             # Internal runtime implementation
│   ├── coordinator.py     # DefaultDecisionCoordinator
│   ├── runtime.py         # StrategyRuntime factory
│   └── stream_controller.py  # Persistence and streaming
├── data/                  # Market data sources
│   ├── interfaces.py      # BaseMarketDataSource
│   └── market.py          # SimpleMarketDataSource (CCXT)
├── features/              # Feature computation
│   ├── interfaces.py      # BaseFeaturesPipeline, CandleBasedFeatureComputer
│   ├── pipeline.py        # DefaultFeaturesPipeline
│   ├── candle.py          # SimpleCandleFeatureComputer
│   └── market_snapshot.py # MarketSnapshotFeatureComputer
├── decision/              # Decision composers
│   ├── interfaces.py      # BaseComposer
│   └── prompt_based/
│       ├── composer.py    # LlmComposer
│       └── system_prompt.py
├── execution/             # Trade execution
│   ├── interfaces.py      # BaseExecutionGateway
│   ├── factory.py         # Gateway factory
│   ├── paper_trading.py   # PaperExecutionGateway
│   └── ccxt_trading.py    # CCXTExecutionGateway (live)
├── portfolio/             # Portfolio management
│   ├── interfaces.py      # BasePortfolioService
│   └── in_memory.py       # InMemoryPortfolioService
└── trading_history/       # History and digest
    ├── interfaces.py      # BaseHistoryRecorder, BaseDigestBuilder
    ├── recorder.py        # InMemoryHistoryRecorder
    └── digest.py          # RollingDigestBuilder
```

## Data Flow (Decision Cycle)

Each decision cycle follows this pipeline:

1. **Portfolio State**: Coordinator fetches current `PortfolioView` (positions, cash, constraints)
2. **Data Collection**: Pipeline pulls market data (candles, tickers, funding rates, etc.)
3. **Feature Computation**: Pipeline computes `FeatureVector[]` from raw data
4. **Context Assembly**: Coordinator builds `ComposeContext` with features, portfolio, digest, and constraints
5. **Decision**: Composer (LLM + guardrails) produces normalized `TradeInstruction[]`
6. **Execution**: Gateway executes instructions and returns `TxResult[]`
7. **Portfolio Update**: Service applies trades to update positions and metrics
8. **History**: Recorder checkpoints features, instructions, trades, and summary
9. **Digest**: Builder updates `TradeDigest` for next cycle's context

```text
                                        ┌─────────────┐
                                        │  Portfolio  │
                                        │    View     │
                                        └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Market    │───▶│   Features   │───▶│   Context   │
│    Data     │    │   Pipeline   │    │  Assembly   │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  Composer   │
                                       │             │
                                       └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  Execution  │
                                       │   Gateway   │
                                       └──────┬──────┘
                                              │
                                              ▼
       ┌──────────────────────────────────────┴────────────────┐
       │                                                       │
       ▼                                                       ▼
┌─────────────┐                                         ┌─────────────┐
│   History   │                                         │  Portfolio  │
│   Recorder  │                                         │   Update    │
└──────┬──────┘                                         └─────────────┘
       │
       ▼
┌─────────────┐
│   Digest    │
│   Builder   │
└─────────────┘
```

## Core Data Models

### Configuration

UserRequest

- `llm_model_config: LLMModelConfig` — AI model settings
- `exchange_config: ExchangeConfig` — Trading mode, exchange, credentials
- `trading_config: TradingConfig` — Strategy parameters

TradingConfig

- `strategy_name?: str` — Display name
- `initial_capital: float` — Starting capital (USD)
- `max_leverage: float` — Maximum leverage allowed
- `max_positions: int` — Concurrent position limit
- `symbols: List[str]` — Instruments to trade (e.g., `["BTC-USDT", "ETH-USDT"]`)
- `decide_interval: int` — Seconds between cycles
- `custom_prompt?: str` — Custom strategy prompt
- `prompt_text?: str` — Additional prompt text

### Market Data

Candle

- `ts: int` — Timestamp (milliseconds)
- `instrument: InstrumentRef` — Symbol reference
- `open, high, low, close, volume: float` — OHLCV data
- `interval: str` — Timeframe (e.g., "1m", "1h")

FeatureVector

- `ts: int` — Feature timestamp
- `instrument: InstrumentRef` — Associated symbol
- `values: Dict[str, float]` — Feature key-value pairs
- `meta?: Dict[str, Any]` — Optional metadata (interval, group_by_key, etc.)

### Portfolio

PositionSnapshot

- `instrument: InstrumentRef`
- `quantity: float` — Signed quantity (+long, -short)
- `avg_price?: float` — Average entry price
- `mark_price?: float` — Current market price
- `unrealized_pnl?: float` — Unrealized profit/loss
- `leverage?: float` — Applied leverage
- `entry_ts?: int` — Entry timestamp

PortfolioView

- `strategy_id: str`
- `ts: int` — Snapshot timestamp
- `account_balance: float` — Cash balance
- `positions: Dict[str, PositionSnapshot]` — Active positions by symbol
- `total_value?: float` — Portfolio equity
- `total_unrealized_pnl?: float` — Sum of position unrealized PnL
- `buying_power?: float` — Available buying power
- `constraints?: Constraints` — Position and leverage limits

### Decision

ComposeContext

- `ts: int` — Cycle timestamp
- `compose_id: str` — Unique cycle identifier
- `strategy_id: str`
- `features: List[FeatureVector]` — Computed features
- `portfolio: PortfolioView` — Current portfolio state
- `digest: TradeDigest` — Historical performance summary

TradeInstruction

- `instruction_id: str` — Unique instruction ID
- `compose_id: str` — Parent cycle ID
- `instrument: InstrumentRef`
- `side: TradeSide` — BUY or SELL
- `quantity: float` — Order quantity
- `leverage?: float` — Applied leverage
- `max_slippage_bps?: int` — Maximum slippage (basis points)
- `meta?: Dict` — Optional metadata

### Execution

TxResult

- `instruction_id: str`
- `instrument: InstrumentRef`
- `side: TradeSide`
- `status: TxStatus` — FILLED, PARTIAL, REJECTED, ERROR
- `requested_qty: float`
- `filled_qty: float`
- `avg_exec_price?: float`
- `fee_cost?: float`
- `leverage?: float`

### History

TradeHistoryEntry

- `trade_id: str`
- `compose_id: str` — Originating cycle
- `instruction_id: str` — Originating instruction
- `instrument: InstrumentRef`
- `side: TradeSide`
- `type: TradeType` — LONG or SHORT
- `quantity: float`
- `entry_price?, exit_price?: float`
- `entry_ts?, exit_ts?: int`
- `realized_pnl?: float` — Profit/loss on close
- `holding_ms?: int` — Position duration

TradeDigest

- `ts: int`
- `by_instrument: Dict[str, TradeDigestEntry]`
- `sharpe_ratio?: float` — Portfolio Sharpe ratio

**TradeDigestEntry** (per-symbol stats)

- `trade_count: int`
- `realized_pnl: float`
- `win_rate?: float`
- `avg_holding_ms?: int`
- `last_trade_ts?: int`

---

## Integration Guide

### Quick Start: Using the Default Agent

The simplest way to create a trading agent is to use `prompt_strategy_agent`, which provides default implementations for all components:

```python
# python/valuecell/agents/prompt_strategy_agent/__main__.py
import asyncio
from valuecell.core.agent import create_wrapped_agent
from .core import StrategyAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(StrategyAgent)
    asyncio.run(agent.serve())
```

**StrategyAgent** (in `core.py`) extends `BaseStrategyAgent` and uses:

- `DefaultFeaturesPipeline`: Fetches candles and computes technical indicators
- `LlmComposer`: LLM-based decision making with guardrails

To run:

```bash
cd python/valuecell/agents/prompt_strategy_agent
python -m valuecell.agents.prompt_strategy_agent
```

### Custom Agent: Override Specific Components

Create a custom agent by subclassing `BaseStrategyAgent` and overriding extension points:

#### Example 1: Custom Feature Pipeline

```python
from valuecell.agents.common.trading.base_agent import BaseStrategyAgent
from valuecell.agents.common.trading.features import BaseFeaturesPipeline
from valuecell.agents.common.trading.models import (
    FeaturesPipelineResult,
    FeatureVector,
    UserRequest,
)

class MyFeaturesPipeline(BaseFeaturesPipeline):
    """Custom pipeline with specialized indicators."""
    
    def __init__(self, request: UserRequest):
        self.request = request
        self.symbols = request.trading_config.symbols
        # Initialize custom data sources, indicators, etc.
    
    async def build(self) -> FeaturesPipelineResult:
        features = []
        # Fetch data and compute custom features
        # ... your logic here ...
        return FeaturesPipelineResult(features=features)


class MyCustomAgent(BaseStrategyAgent):
    """Agent with custom feature computation."""
    
    async def _build_features_pipeline(
        self, request: UserRequest
    ) -> BaseFeaturesPipeline | None:
        return MyFeaturesPipeline(request)
    
    async def _create_decision_composer(self, request: UserRequest):
        # Use default LLM composer
        return None
```

#### Example 2: Custom Decision Composer

```python
from valuecell.agents.common.trading.decision import BaseComposer
from valuecell.agents.common.trading.models import (
    ComposeContext,
    ComposeResult,
    TradeInstruction,
)

class RuleBasedComposer(BaseComposer):
    """Simple rule-based decision maker (no LLM)."""
    
    def __init__(self, request: UserRequest):
        self.request = request
    
    async def compose(self, context: ComposeContext) -> ComposeResult:
        instructions = []
        # Implement your trading rules
        # Example: Buy when RSI < 30, sell when RSI > 70
        for fv in context.features:
            rsi = fv.values.get("rsi")
            if rsi and rsi < 30:
                # Create buy instruction
                pass
            elif rsi and rsi > 70:
                # Create sell instruction
                pass
        
        return ComposeResult(
            instructions=instructions,
            rationale="Rule-based signals"
        )


class RuleBasedAgent(BaseStrategyAgent):
    """Agent using rule-based decisions."""
    
    async def _build_features_pipeline(self, request: UserRequest):
        # Use default pipeline
        return None
    
    async def _create_decision_composer(self, request: UserRequest):
        return RuleBasedComposer(request)
```

#### Example 3: Lifecycle Hooks

```python
class MonitoredAgent(BaseStrategyAgent):
    """Agent with custom monitoring and logging."""
    
    async def _on_start(self, runtime, request):
        """Called once after runtime creation."""
        self.cycle_count = 0
        print(f"Strategy {runtime.strategy_id} starting...")
    
    async def _on_cycle_result(self, result, runtime, request):
        """Called after each cycle completes."""
        self.cycle_count += 1
        print(f"Cycle {self.cycle_count}: "
              f"{len(result.trades)} trades, "
              f"PnL: {result.strategy_summary.realized_pnl}")
        
        # Send metrics to external monitoring
        # ... custom logic ...
    
    async def _on_stop(self, runtime, request, reason):
        """Called before finalization."""
        print(f"Strategy stopping: {reason}")
        print(f"Total cycles: {self.cycle_count}")
    
    async def _build_features_pipeline(self, request):
        return None  # Use defaults
    
    async def _create_decision_composer(self, request):
        return None  # Use defaults
```

### Creating a Complete Custom Agent Module

**Directory Structure:**

```text
python/valuecell/agents/my_agent/
├── __init__.py
├── __main__.py          # Entry point
├── core.py              # Agent implementation
├── features.py          # Custom features (optional)
├── composer.py          # Custom composer (optional)
└── templates/
    └── strategy.txt     # Strategy prompt template
```

**`__main__.py`:**

```python
import asyncio
from valuecell.core.agent import create_wrapped_agent
from .core import MyAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(MyAgent)
    asyncio.run(agent.serve())
```

**`core.py`:**

```python
from valuecell.agents.common.trading.base_agent import BaseStrategyAgent
from valuecell.agents.common.trading.models import UserRequest
from .features import MyFeaturesPipeline  # if custom
from .composer import MyComposer  # if custom

class MyAgent(BaseStrategyAgent):
    async def _build_features_pipeline(self, request: UserRequest):
        # Return custom pipeline or None for default
        return MyFeaturesPipeline(request)
    
    async def _create_decision_composer(self, request: UserRequest):
        # Return custom composer or None for default
        return MyComposer(request)
```

**Run your agent:**

```bash
cd python/valuecell/agents/my_agent
python -m valuecell.agents.my_agent
```

### Live Trading Setup

For live trading with real exchanges:

**Set trading mode to LIVE:**

```json
{
  "exchange_config": {
    "trading_mode": "live",
    "exchange_id": "binance",
    "api_key": "YOUR_API_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "testnet": true  // Use testnet first!
  }
}
```

**The runtime automatically:**

- Fetches real account balance
- Sets `initial_capital` to available cash
- Uses `CCXTExecutionGateway` for order submission

**Always test on testnet first** before using real funds

### Testing Strategies

#### Paper Trading (Default)

```json
{
  "exchange_config": {
    "trading_mode": "virtual",
    "fee_bps": 10.0  // 0.1% simulated fees
  }
}
```

Paper trading uses `PaperExecutionGateway` which:

- Simulates order fills at market price ± slippage
- Applies configurable fees
- No real exchange connection needed

#### Backtesting

Create a custom `BaseMarketDataSource` that replays historical data:

```python
from valuecell.agents.common.trading.data import BaseMarketDataSource
from valuecell.agents.common.trading.models import Candle

class BacktestDataSource(BaseMarketDataSource):
    def __init__(self, historical_data):
        self.data = historical_data
        self.current_index = 0
    
    async def get_recent_candles(self, symbols, interval, lookback):
        # Return historical candles for current timestamp
        candles = self.data[self.current_index]
        self.current_index += 1
        return candles
    
    async def get_market_snapshot(self, symbols):
        # Return snapshot from historical data
        return {}
```

Then use it in your custom pipeline.

### Extension Points Summary

| Component | Method | Purpose |
|-----------|--------|---------|
| **Features** | `_build_features_pipeline()` | Define how market data is fetched and processed |
| **Decision** | `_create_decision_composer()` | Customize trading logic (LLM, rules, ML) |
| **Lifecycle** | `_on_start()` | Initialize resources after runtime creation |
| **Lifecycle** | `_on_cycle_result()` | Monitor/log each cycle result |
| **Lifecycle** | `_on_stop()` | Cleanup before finalization |

### Best Practices

1. **Start with defaults**: Use `prompt_strategy_agent` as a template
2. **Override incrementally**: Only customize what you need
3. **Type safety**: Use Pydantic models for all data contracts
4. **Async operations**: Mark I/O operations as `async`
5. **Error handling**: Hooks swallow exceptions to prevent crashes
6. **Testnet first**: Always test live trading on testnet
7. **Monitor carefully**: Use lifecycle hooks for observability

### Common Patterns

#### Adding Custom Indicators

```python
class CustomFeaturesPipeline(BaseFeaturesPipeline):
    async def build(self):
        # Fetch candles
        candles = await self.market_data.get_recent_candles(...)
        
        # Compute standard indicators
        rsi = compute_rsi(candles)
        macd = compute_macd(candles)
        
        # Add custom indicators
        my_signal = compute_custom_indicator(candles)
        
        features = []
        for symbol in symbols:
            features.append(FeatureVector(
                ts=timestamp,
                instrument=InstrumentRef(symbol=symbol),
                values={
                    "rsi": rsi[symbol],
                    "macd": macd[symbol],
                    "custom_signal": my_signal[symbol],
                }
            ))
        
        return FeaturesPipelineResult(features=features)
```

#### Combining LLM with Rules

```python
class HybridComposer(BaseComposer):
    def __init__(self, request):
        self.llm_composer = LlmComposer(request)
        self.request = request
    
    async def compose(self, context):
        # Get LLM suggestions
        llm_result = await self.llm_composer.compose(context)
        
        # Apply additional rule filters
        filtered_instructions = []
        for inst in llm_result.instructions:
            if self._passes_risk_check(inst, context):
                filtered_instructions.append(inst)
        
        return ComposeResult(
            instructions=filtered_instructions,
            rationale=f"LLM + risk filters: {llm_result.rationale}"
        )
    
    def _passes_risk_check(self, inst, context):
        # Custom risk rules
        return True
```

### Debugging

Enable detailed logging:

```python
import logging
from loguru import logger

logger.add("strategy_{time}.log", level="DEBUG")
```

The framework logs:

- Cycle start/end with compose_id
- Instruction count and details
- Execution results and fills
- Portfolio updates
- Error traces with context

---

## Advanced Topics

### Custom Execution Gateway

Implement `BaseExecutionGateway` to integrate custom execution logic:

```python
from valuecell.agents.common.trading.execution import BaseExecutionGateway
from valuecell.agents.common.trading.models import (
    TradeInstruction,
    TxResult,
    TxStatus,
)

class MyExecutionGateway(BaseExecutionGateway):
    async def execute(self, instructions, market_features):
        results = []
        for inst in instructions:
            # Your execution logic
            result = TxResult(
                instruction_id=inst.instruction_id,
                instrument=inst.instrument,
                side=inst.side,
                status=TxStatus.FILLED,
                requested_qty=inst.quantity,
                filled_qty=inst.quantity,
                avg_exec_price=100.0,  # from your system
            )
            results.append(result)
        return results
```

### Custom Portfolio Service

Override portfolio management for complex accounting:

```python
from valuecell.agents.common.trading.portfolio import BasePortfolioService

class CustomPortfolioService(BasePortfolioService):
    def get_view(self):
        # Return custom PortfolioView
        pass
    
    def apply_trades(self, trades, market_features):
        # Update internal state
        pass
```

### Persistence Integration

Use `StreamController` to persist strategy state to your database. The framework already handles:

- Initial portfolio snapshot
- Cycle results (compose cycles, instructions, execution details)
- Final cleanup and status updates

See `_internal/stream_controller.py` for persistence logic.
