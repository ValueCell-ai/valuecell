#!/bin/bash

# Color codes for output highlighting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Function to print highlighted command
highlight_command() {
    echo -e "${BLUE}Running: $1${NC}"
}

# Check if current directory is project root
if [ ! -f ".gitignore" ] || [ ! -d "python" ] || [ ! -d "python/third_party" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory.${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' command not found. Please install 'uv' (e.g., brew install uv).${NC}"
    exit 1
fi

# Prepare environments
echo -e "${GREEN}Project root confirmed. Preparing environments...${NC}"

echo -e "${YELLOW}Setting up main Python environment...${NC}"
pushd ./python
highlight_command "uv venv --python 3.12"
uv venv --python 3.12
highlight_command "uv sync --group dev"
uv sync --group dev
popd
echo -e "${GREEN}Main environment setup complete.${NC}"

echo -e "${YELLOW}Setting up third-party environments...${NC}"
echo -e "${YELLOW}Setting up ai-hedge-fund environment...${NC}"
pushd ./python/third_party/ai-hedge-fund
highlight_command "uv venv --python 3.12"
uv venv --python 3.12
highlight_command "uv sync"
uv sync
popd
echo -e "${GREEN}ai-hedge-fund environment setup complete.${NC}"

echo -e "${YELLOW}Setting up TradingAgents environment...${NC}"
pushd ./python/third_party/TradingAgents
highlight_command "uv venv --python 3.12"
uv venv --python 3.12
highlight_command "uv sync"
uv sync
popd
echo -e "${GREEN}TradingAgents environment setup complete.${NC}"
echo -e "${GREEN}All environments are set up.${NC}"