# Contributing to ValueCell
TODO: Write contribution guidelines

## Development

### Python Code
**Dev Environment**

To install the development dependencies:

```bash
# Way 1: using --extra dev
uv sync --extra dev

# Way 2: using uvpip
uv pip install --editable ".[dev]"
```

**Lint and Test**

You can run lint and test in the project root directory:
```bash
make format
make lint
make test
```

**Pull Request**

Create pull requests to the `main` branch.
You'd better create a pull request with a github `Labels`, this will help us to review your PR.