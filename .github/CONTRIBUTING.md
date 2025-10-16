# Contributing to ValueCell

Thank you for your interest in contributing to ValueCell! We appreciate your help in making this multi-agent financial platform better. This guide will help you get started with contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md). Please read it before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Relevant logs** from `logs/{timestamp}/*.log`

### Suggesting Features

Feature requests are welcome! Please:

- **Check existing issues** to avoid duplicates
- **Describe the feature** and its use case clearly
- **Explain why** this feature would benefit ValueCell users

### Contributing Code

We welcome code contributions! See the [Development Setup](#development-setup) section below to get started.

## Development Setup

### Prerequisites

- **Python**: 3.12 or higher
- **[uv](https://docs.astral.sh/uv/)**: Fast Python package manager
- **[bun](https://bun.sh/)**: JavaScript/TypeScript toolkit (for frontend)

### Initial Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/valuecell.git
   cd valuecell
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Python Development

**Install dependencies:**

```bash
# Method 1: Using sync (recommended)
cd python
uv sync --extra dev

# Method 2: Using pip
uv pip install --editable ".[dev]"
```

**Run the application:**

```bash
# From project root
bash start.sh  # Linux/macOS
# or
.\start.ps1    # Windows
```

### Frontend Development

**Install dependencies:**

```bash
cd frontend
bun install
```

## Code Style

### Python

We use **Ruff** for linting and formatting, and **isort** for import sorting.

**Run formatting:**

```bash
make format
```

**Run linting:**

```bash
make lint
```

### Frontend

We use **Biome** for linting and formatting.

**Run checks:**

```bash
cd frontend
bun run check:fix  # Auto-fix all issues
```

**Key style rules:**

- Use TypeScript for type safety
- Follow React best practices
- Use functional components with hooks
- Maintain component modularity

## Testing

### Python Tests

**Run all tests:**

```bash
make test
```

**Run specific tests:**

```bash
uv run pytest ./python/valuecell/path/to/test.py
```

**Test requirements:**

- Write tests for new features
- Maintain or improve test coverage
- Ensure all tests pass before submitting PR

### Frontend Tests

Frontend testing guidelines are being established. Please ensure your code follows existing patterns.

## Commit Guidelines

We follow conventional commit messages for clarity and automation:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(agents): add European market support
fix(sec-agent): resolve SEC filing parsing error
docs: update installation instructions
```

## Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**
   - Follow the code style guidelines
   - Write or update tests
   - Update documentation if needed

3. **Run checks locally**

   ```bash
   make format  # Format code
   make lint    # Check linting
   make test    # Run tests
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to your fork**

   ```bash
   git push origin feat/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the [ValueCell repository](https://github.com/ValueCell-ai/valuecell)
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template
   - Add appropriate labels
   - Request review

### PR Requirements

- ✅ All CI checks pass
- ✅ Code follows style guidelines
- ✅ Tests are included and passing
- ✅ Documentation is updated (if applicable)
- ✅ Commits follow commit guidelines
- ✅ PR description clearly explains changes

### Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged

## Questions?

If you have questions:

- 💬 Join our [Discord](https://discord.com/invite/84Kex3GGAh)
- 📧 Email us at public@valuecell.ai
- 🐛 Open an issue for bug reports

---

Thank you for contributing to ValueCell! 🚀