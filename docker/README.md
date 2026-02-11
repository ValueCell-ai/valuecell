# Docker Deployment Guide

This project supports running frontend and backend services using Docker containers.

## Quick Start

### 1. Configure Environment Variables

```bash
cp .env.example .env
```

Edit the `.env` file with your API keys and preferences. This configuration file is shared across all agents. See [Configuration Guide](../docs/CONFIGURATION_GUIDE.md) for details.

> **Note**: Some runtime environment variables (like `API_HOST`, `API_PORT`, `CORS_ORIGINS`) are already configured in `docker-compose.yml`. 

### 2. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Start backend only
docker-compose up -d backend

# Start frontend only
docker-compose up -d frontend
```

### 3. Access Services

- **Frontend**: http://localhost:1420
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Service Description

### Backend Service

- **Port**: 8000
- **Image**: Based on `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- **Working Directory**: `/app/python`
- **Entrypoint**: `/app/entrypoint.sh` (automatically initializes database if needed)
- **Start Command**: `uv run -m valuecell.server.main`
- **PyPI Mirror**: Configured to use Tsinghua University mirror source
- **Database**: Automatically initialized on first startup if not exists

### Frontend Service

- **Port**: 1420
- **Image**: Based on `oven/bun:1.3.0-slim`
- **Working Directory**: `/app/frontend`
- **Start Command**: `bun run dev`
- **NPM Mirror**: Configured to use Taobao mirror source

## Mirror Source Configuration

Dockerfiles have automatically configured the following mirror sources for faster downloads:

- **Docker Images**: Using `docker.1ms.run` mirror for base images (no additional Docker Desktop configuration needed)
- **APT (Debian)**: Alibaba Cloud mirror
- **PyPI (Python)**: Tsinghua University mirror
- **NPM (Node.js)**: Taobao mirror

> **Note**: The Dockerfiles use `docker.1ms.run` mirror for pulling base images, so you don't need to configure Docker Desktop registry mirrors separately.

## Data Persistence

The following directories/files are mounted to containers, and data will be persisted:

- `./python` → `/app/python` (backend code)
- `./logs` → `/app/logs` (log files)
- `./data` → `/app/data` (database and data files)
  - Database file: `./data/valuecell.db` (automatically created if not exists)
- `./lancedb` → `/app/lancedb` (LanceDB data)
- `./frontend` → `/app/frontend` (frontend code)

> **Note**: The database is automatically initialized on first startup if it doesn't exist. The entrypoint script checks and initializes the database before starting the server.

## Development Mode

In development mode, code changes are automatically reflected in containers (via volume mounts):

```bash
# Start development environment
docker-compose up

# View logs in another terminal
docker-compose logs -f frontend
docker-compose logs -f backend
```

## Production Deployment

For production environments, it is recommended to:

1. Modify port mappings in `docker-compose.yml`
2. Use environment variable files to manage configuration
3. Configure reverse proxy (such as Nginx)
4. Use Docker secrets to manage sensitive information
5. Consider using multi-stage builds to optimize image size

## Troubleshooting

### View Container Status

```bash
docker-compose ps
```

### View Container Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend

# Real-time logs
docker-compose logs -f
```

### Enter Container for Debugging

```bash
# Enter backend container
docker-compose exec backend bash

# Enter frontend container
docker-compose exec frontend sh
```

### Rebuild Images

```bash
# Force rebuild
docker-compose build --no-cache

# Rebuild and start
docker-compose up -d --build
```

### Network Issues

If encountering network connection issues:

1. The Dockerfiles already use `docker.1ms.run` mirror for base images, which should provide good download speeds
2. If you still experience issues, try using a proxy:
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   docker-compose build
   ```

## Environment Variables

Environment variables can be configured via the `.env` file. See [Configuration Guide](../docs/CONFIGURATION_GUIDE.md) for details.

> **Note**: Some runtime variables (`API_HOST`, `API_PORT`, `CORS_ORIGINS`) are configured in `docker-compose.yml`.

### Build-time Environment Variables

These variables are already configured in Dockerfiles and used during image build:

- `UV_INDEX_URL`: PyPI mirror address (configured in `Dockerfile.backend` as Tsinghua source)
- `BUN_CONFIG_REGISTRY`: NPM mirror address (configured in `Dockerfile.frontend` as Taobao source)

> **Note**: `UV_INDEX_URL` and `BUN_CONFIG_REGISTRY` are build-time variables set in the Dockerfiles. You don't need to configure them in `docker-compose.yml` or `.env` files as they only affect the image build process, not the running containers.
