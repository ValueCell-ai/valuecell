#!/bin/bash

# TradingAgents Adapter启动脚本

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

echo "🚀 Starting TradingAgents Adapter..."
echo "📁 Project directory: ${SCRIPT_DIR}"
echo "🐍 Python environment directory: ${PYTHON_DIR}"

# Activate virtual environment
if [ -f "${PYTHON_DIR}/.venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source "${PYTHON_DIR}/.venv/bin/activate"
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Set environment variables
export PYTHONPATH="${SCRIPT_DIR}:${PYTHON_DIR}:${PYTHONPATH}"
export AGENT_PORT="${AGENT_PORT:-10002}"

echo "🌐 Agent will start on port ${AGENT_PORT}"

# Switch to TradingAgents directory
cd "${SCRIPT_DIR}"

# Start adapter
echo "🎯 Starting TradingAgents Adapter..."
uv run start_adapter.py

echo "👋 TradingAgents Adapter closed"
