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

# Check current directory and switch to python if needed
if [ -d "python" ] && [ -f "python/pyproject.toml" ] && [ -f ".gitignore" ]; then
    echo -e "${YELLOW}Detected project root. Switching to python directory...${NC}"
    cd python
elif [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: This script must be run from the project python directory or project root. You are in $(pwd)${NC}"
    exit 1
fi

# Final check if in python directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Failed to switch to python directory. You are in $(pwd)${NC}"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' command not found. Please install 'uv' (e.g., brew install uv).${NC}"
    exit 1
fi

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Starting environment preparation...${NC}"
echo -e "${BLUE}==========================================${NC}"

# Prepare environments
echo -e "${GREEN}Project root confirmed. Preparing environments...${NC}"

echo -e "${YELLOW}Setting up main Python environment...${NC}"
if [ ! -d ".venv" ]; then
    highlight_command "uv venv --python 3.12"
    uv venv --python 3.12
else
    echo -e "${YELLOW}.venv already exists, skipping venv creation.${NC}"
fi
highlight_command "uv sync --group dev"
uv sync --group dev
uvx playwright install --with-deps chromium
echo -e "${GREEN}Main environment setup complete.${NC}"

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}All environments are set up.${NC}"
echo -e "${GREEN}==========================================${NC}"