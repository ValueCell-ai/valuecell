# Docker 部署指南

本项目支持使用 Docker 容器运行前端和后端服务。

## 快速开始

### 1. 配置 Docker 镜像加速器（推荐）

为了加快 Docker 镜像拉取速度，建议配置国内镜像源。

#### Windows/Mac (Docker Desktop)

1. 打开 Docker Desktop
2. 进入 Settings → Docker Engine
3. 添加以下配置：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

4. 点击 "Apply & Restart"

#### Linux

创建或编辑 `/etc/docker/daemon.json`：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 2. 准备环境文件

在项目根目录创建 `.env` 文件（如果不存在），包含必要的环境变量：

```bash
# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 数据库配置（可选）
VALUECELL_SQLITE_DB=sqlite:///valuecell.db

# CORS 配置
CORS_ORIGINS=http://localhost:1420,http://localhost:3000
```

### 3. 构建并启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 只启动后端
docker-compose up -d backend

# 只启动前端
docker-compose up -d frontend
```

### 4. 访问服务

- **前端**: http://localhost:1420
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 5. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除卷
docker-compose down -v
```

## 服务说明

### Backend 服务

- **端口**: 8000
- **镜像**: 基于 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- **工作目录**: `/app/python`
- **启动命令**: `uv run -m valuecell.server.main`
- **PyPI 镜像**: 已配置使用清华大学镜像源

### Frontend 服务

- **端口**: 1420
- **镜像**: 基于 `oven/bun:1.3.0-slim`
- **工作目录**: `/app/frontend`
- **启动命令**: `bun run dev`
- **NPM 镜像**: 已配置使用淘宝镜像源

## 国内镜像源配置

Dockerfile 已自动配置以下国内镜像源：

- **APT (Debian)**: 阿里云镜像
- **PyPI (Python)**: 清华大学镜像
- **NPM (Node.js)**: 淘宝镜像

## 数据持久化

以下目录/文件会被挂载到容器中，数据会持久化：

- `./python` → `/app/python` (后端代码)
- `./logs` → `/app/logs` (日志文件)
- `./valuecell.db` → `/app/valuecell.db` (数据库)
- `./lancedb` → `/app/lancedb` (LanceDB 数据)
- `./frontend` → `/app/frontend` (前端代码)

## 开发模式

在开发模式下，代码更改会自动反映到容器中（通过卷挂载）：

```bash
# 启动开发环境
docker-compose up

# 在另一个终端中查看日志
docker-compose logs -f frontend
docker-compose logs -f backend
```

## 生产部署

对于生产环境，建议：

1. 修改 `docker-compose.yml` 中的端口映射
2. 使用环境变量文件管理配置
3. 配置反向代理（如 Nginx）
4. 使用 Docker secrets 管理敏感信息
5. 考虑使用多阶段构建优化镜像大小

## 故障排查

### 查看容器状态

```bash
docker-compose ps
```

### 查看容器日志

```bash
# 所有服务
docker-compose logs

# 特定服务
docker-compose logs backend
docker-compose logs frontend

# 实时日志
docker-compose logs -f
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh
```

### 重建镜像

```bash
# 强制重建
docker-compose build --no-cache

# 重建并启动
docker-compose up -d --build
```

### 网络问题

如果遇到网络连接问题：

1. 检查 Docker 镜像加速器配置是否正确
2. 尝试使用代理：
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   docker-compose build
   ```

## 环境变量

可以通过 `.env` 文件或 `docker-compose.yml` 中的 `environment` 部分配置环境变量。

常用环境变量：

- `API_HOST`: 后端 API 主机地址（默认: 0.0.0.0）
- `API_PORT`: 后端 API 端口（默认: 8000）
- `CORS_ORIGINS`: CORS 允许的源（逗号分隔）
- `VALUECELL_SQLITE_DB`: SQLite 数据库路径
- `UV_INDEX_URL`: PyPI 镜像地址（已配置为清华源）
- `BUN_CONFIG_REGISTRY`: NPM 镜像地址（已配置为淘宝源）
