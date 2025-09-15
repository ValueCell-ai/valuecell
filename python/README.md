# ValueCell Python Package

ValueCell is a community-driven, multi-agent platform for financial applications.

## Installation

### Development Installation

Install the package in development mode with all dependencies:

```bash
uv pip install -e ".[dev]"
```

### Production Installation

```bash
uv sync
```

## Project Structure

- `valuecell/` - Main package
  - `adapters/` - External system adapters
  - `agents/` - Agent implementations
  - `api/` - FastAPI application
  - `core/` - Core types and utilities
  - `services/` - Business logic services
  - `examples/` - Usage examples
  - `tests/` - Test suite

## Running Tests

```bash
pytest
```

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
