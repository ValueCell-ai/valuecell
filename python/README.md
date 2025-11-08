# ValueCell Python Package

> A community-driven, multi-agent platform for financial applications — typed, async-first, and built for orchestration.

## Highlights

- Async, re-entrant orchestrator: streaming `process_user_input` can pause for human-in-the-loop (HITL) and resume safely.
- Planner with HITL: pauses on missing info/risky steps via async `UserInputRequest`, resumes after user feedback to produce an adequate plan.
- Streaming pipeline: `Response` → `ResponseBuffer` (buffered vs immediate with stable item_id) → `ResponseRouter` to UI and Store.
- Agent2Agent (A2A) integration: first-class support via a2a-sdk for agent-to-agent protocols, message schemas, and optional HTTP server interop.
- Conversation memory: in-memory/SQLite stores enable reproducible history, fast "resume from last", and auditability.
- Robustness & extensibility: typed events/errors, router side-effects (e.g., fail task), and clear seams to add agents, stores, transports, and planner logic.

See detailed flow diagrams and design notes in `../docs/CORE_ARCHITECTURE.md`.

## Quickstart

Set up the environment and verify your install:

```bash
uv sync --group dev
uv run python -c "import valuecell as vc; print(vc.__version__)"
```

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

## Requirements

- Python >= 3.12
- Dependencies managed via `pyproject.toml`

## OKX Trading (Preview)

Add OKX credentials to `.env` (or export them before launch):

```bash
AUTO_TRADING_EXCHANGE=okx
OKX_NETWORK=paper          # switch to mainnet only after validation
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_API_PASSPHRASE=...
OKX_ALLOW_LIVE_TRADING=false
OKX_MARGIN_MODE=cash       # or cross / isolated
```

Launch with `./start.sh --exchange okx --network paper` to route the Auto Trading agent through OKX. Flip `OKX_ALLOW_LIVE_TRADING=true` only when you're ready for real execution.
