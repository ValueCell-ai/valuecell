#!/bin/bash
# Docker 快速启动脚本

set -e

echo "=========================================="
echo "ValueCell Docker 启动脚本"
echo "=========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 Docker。请先安装 Docker。"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: 未找到 Docker Compose。请先安装 Docker Compose。"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "警告: 未找到 .env 文件。将使用默认配置。"
    echo "建议创建 .env 文件并配置必要的环境变量。"
fi

# 构建并启动服务
echo ""
echo "构建 Docker 镜像..."
docker-compose build

echo ""
echo "启动服务..."
docker-compose up -d

echo ""
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "服务状态:"
docker-compose ps

echo ""
echo "=========================================="
echo "服务已启动！"
echo "前端: http://localhost:1420"
echo "后端 API: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""

