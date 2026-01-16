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

# Use Chinese mirror if UV_INDEX_URL is not set
if [ -z "${UV_INDEX_URL:-}" ]; then
    echo -e "${YELLOW}Using Chinese mirror for faster download (Tsinghua)...${NC}"
    export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
fi

highlight_command "uv sync --group dev"
echo -e "${YELLOW}开始安装依赖，这可能需要几分钟时间...${NC}"
if [ -n "${UV_INDEX_URL:-}" ]; then
    echo -e "${BLUE}使用镜像: ${UV_INDEX_URL}${NC}"
else
    echo -e "${YELLOW}未设置镜像，使用默认源（可能较慢）${NC}"
fi
echo ""

# 执行 uv sync，显示详细输出
if uv sync --group dev; then
    echo -e "${GREEN}依赖安装完成！${NC}"
else
    echo -e "${RED}依赖安装失败！${NC}"
    echo -e "${YELLOW}可能的原因：${NC}"
    echo "  1. 网络连接问题"
    echo "  2. 镜像源不可用"
    echo "  3. 依赖包版本冲突"
    echo ""
    echo -e "${BLUE}尝试解决方案：${NC}"
    echo "  1. 检查网络连接"
    echo "  2. 尝试切换镜像源: export UV_INDEX_URL='https://mirrors.aliyun.com/pypi/simple/'"
    echo "  3. 查看详细错误信息: uv sync --group dev --verbose"
    exit 1
fi
uvx playwright install --with-deps chromium
echo -e "${GREEN}Main environment setup complete.${NC}"

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}All environments are set up.${NC}"
echo -e "${GREEN}==========================================${NC}"