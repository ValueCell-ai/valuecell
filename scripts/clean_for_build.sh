#!/bin/bash
# Clean Python directory before building for smaller app size

PYTHON_DIR="/Users/dighuang/GitHub/valuecell/python"

echo "🧹 Cleaning Python directory for build..."

# Remove virtual environment
echo "  Removing .venv..."
rm -rf "$PYTHON_DIR/.venv"

# Remove Python cache
echo "  Removing __pycache__..."
find "$PYTHON_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PYTHON_DIR" -type f -name "*.pyc" -delete
find "$PYTHON_DIR" -type f -name "*.pyo" -delete

# Remove build artifacts
echo "  Removing build artifacts..."
rm -rf "$PYTHON_DIR/build"
rm -rf "$PYTHON_DIR/dist"
find "$PYTHON_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove test and linting cache
echo "  Removing test/lint cache..."
rm -rf "$PYTHON_DIR/.pytest_cache"
rm -rf "$PYTHON_DIR/.ruff_cache"
rm -rf "$PYTHON_DIR/.mypy_cache"
rm -rf "$PYTHON_DIR/.tox"

echo "✅ Python directory cleaned!"
echo "📦 Ready for building..."

