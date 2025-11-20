# Guidelines

## Python Programming

### Python Environment

* Package manager: uv
* Virtual environment: `./python/.venv`
* Testing command: `uv run pytest`

### Imports

* Avoid inline imports unless required to break a circular dependency.
* If you import more than three names from a single module, prefer qualified imports:
  * Prefer: `import pathlib; pathlib.Path, pathlib.PurePath`
  * Avoid: `from pathlib import Path, PurePath, PurePosixPath, ...`
* Postpone changes to `__init__` and `__all__` until APIs stabilize.
* Use TYPE_CHECKING for imports only needed for type hints.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypkg.schemas import AgentConfig
```

### Runtime Checks

* Avoid excessive use of `getattr`, `hasattr`, and runtime type checks.
* If an object is a pydantic `BaseModel`, prefer using its validated attributes and type annotations instead of probing attributes at runtime.
* Rely on pydantic validation, model validators, and type hints; prefer `TypedDict` or `Protocol` for structural typing when appropriate.
* When runtime checks are necessary, make them explicit, minimal, and well-documented so the reason for the guard is clear.

### Async-First Design

* Prefer asynchronous APIs for I/O-bound work.
* Use asyncio or anyio; for HTTP, prefer httpx (async client).
* Ensure clear async boundaries: public APIs and I/O paths should be async.
* Provide minimal sync adapters only when needed, and document them.

```python
import asyncio
from loguru import logger
import httpx

async def fetch_agent_state(url: str, timeout_s: float) -> dict:
    """Fetch agent state from a remote endpoint."""
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Fetched state from {url}", url=url)
        return data

def fetch_agent_state_sync(url: str, timeout_s: float) -> dict:
    """Synchronous adapter. Prefer the async variant."""
    return asyncio.run(fetch_agent_state(url, timeout_s))
```

### Logging

* Use loguru; placeholders must be {} rather than %.
* Log key events at info; avoid excessive logging.
* Do not log sensitive data.
* Use `logger.exception` sparingly: only for truly unexpected errors that require stack traces for debugging. For expected or recoverable errors, prefer `logger.warning` or `logger.error` with explicit context.
* Prefer `logger.warning` for recoverable issues, degraded states, or when an operation can continue despite an error.

```python
from loguru import logger

def process_items(items: list[str]) -> int:
    """Process items and return count."""
    count = len(items)
    logger.info("Processing {count} items", count=count)
    # ...
    logger.info("Processed {count} items", count=count)
    return count

# Good: expected error, use warning with context
async def send_notification(msg: str) -> None:
    """Send notification; log warning if it fails (non-critical)."""
    try:
        await notify_service(msg)
    except NetworkError as exc:
        logger.warning("Notification failed, continuing: {err}", err=str(exc))

# Good: unexpected error requiring investigation, use exception
async def critical_operation() -> None:
    """Perform critical operation that should never fail."""
    try:
        await process_critical_data()
    except Exception:
        logger.exception("Critical operation failed unexpectedly")
        raise
```

### Type Hints and Comments

* Add type hints across public and internal APIs.
* Comments and docstrings should be in English and explain why, not only what.
* Use Protocols and TypedDict or pydantic models where appropriate.
* Avoid excessive literal dict access (for example, using `obj['key']` everywhere); prefer typed structures such as `dataclass`, pydantic models, or `TypedDict` for clearer contracts and better type safety.

### Error Handling

* Keep try-except depth to at most two levels.
* Catch specific exceptions. Re-raise with context if needed.
* Prefer explicit None checks and guard clauses over broad exception use.

```python
import json
from loguru import logger

def parse_payload(raw: str) -> dict:
    """Parse payload; return empty dict on known format errors."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.info("Invalid JSON: {err}", err=str(exc))
        return {}
    return data
```

### Structure and Size

* Avoid nested functions; extract helpers at module level.
* Keep functions under 200 lines. Split into well-named helpers.
* Avoid functions with more than 10 parameters; prefer wrapping parameters in a struct or object.
* Separate concerns: I/O, parsing, business logic, and orchestration.

### Strings and Literals

* Avoid long string literals; wrap lines under 100 characters.
* Avoid magic numbers and ad-hoc string literals. Centralize constants.

```python
# constants.py
DEFAULT_TIMEOUT_S: float = 10.0
MAX_RETRIES: int = 3
```

### Boolean Logic

* Be careful with or where 0, empty, or False may be meaningful.
* Prefer explicit checks:

```python
# Prefer
value = user_value if user_value is not None else default

# Avoid
value = user_value or default
```

### Module and Package Layout

* Group agent core, adapters, and utilities into separate modules.
* Keep public surface small. Delay re-exports in __init__ until stable.
* If circular dependencies appear, refactor shared contracts to a thin shared module (e.g., interfaces.py or contracts.py).
