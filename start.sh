#!/bin/bash
set -Eeuo pipefail

# Simple project launcher with auto-install for bun and uv
# - macOS: use Homebrew to install missing tools
# - other OS: print guidance

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PY_DIR="$SCRIPT_DIR/python"

BACKEND_PID=""
FRONTEND_PID=""

info()  { echo "[INFO]  $*"; }
success(){ echo "[ OK ]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERR ]  $*" 1>&2; }

# Get system config directory (must match Python's get_system_env_dir)
get_system_config_dir() {
  case "$(uname -s)" in
    Darwin)
      echo "$HOME/Library/Application Support/ValueCell"
      ;;
    Linux)
      echo "$HOME/.config/valuecell"
      ;;
    *)
      echo "$HOME/.config/valuecell"
      ;;
  esac
}

# Get port file path
get_port_file_path() {
  echo "$(get_system_config_dir)/backend.port"
}

# Read backend port from port file
read_backend_port() {
  local port_file
  port_file="$(get_port_file_path)"
  if [[ -f "$port_file" ]]; then
    cat "$port_file" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Wait for port file and return the port
wait_for_port_file() {
  local timeout=${1:-30}
  local port_file
  port_file="$(get_port_file_path)"
  local elapsed=0
  
  info "Waiting for backend port file..."
  while [[ ! -f "$port_file" ]] && (( elapsed < timeout )); do
    sleep 0.5
    elapsed=$((elapsed + 1))
  done
  
  if [[ -f "$port_file" ]]; then
    local port
    port=$(cat "$port_file" 2>/dev/null)
    if [[ -n "$port" ]]; then
      success "Backend started on port: $port"
      echo "$port"
      return 0
    fi
  fi
  
  error "Timeout waiting for backend port file"
  return 1
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

ensure_brew_on_macos() {
  if [[ "${OSTYPE:-}" == darwin* ]]; then
    if ! command_exists brew; then
      error "Homebrew is not installed. Please install Homebrew: https://brew.sh/"
      error "Example install: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
      exit 1
    fi
  fi
}

ensure_tool() {
  local tool_name="$1"; shift
  local brew_formula="$1"; shift || true

  if command_exists "$tool_name"; then
    success "$tool_name is installed ($($tool_name --version 2>/dev/null | head -n1 || echo version unknown))"
    return 0
  fi

  case "$(uname -s)" in
    Darwin)
      ensure_brew_on_macos
      info "Installing $tool_name via Homebrew..."
      brew install "$brew_formula"
      ;;
    Linux)
      info "Detected Linux, auto-installing $tool_name..."
      if [[ "$tool_name" == "bun" ]]; then
        curl -fsSL https://bun.sh/install | bash
        # Add Bun default install dir to PATH (current process only)
        if ! command_exists bun && [[ -x "$HOME/.bun/bin/bun" ]]; then
          export PATH="$HOME/.bun/bin:$PATH"
        fi
      elif [[ "$tool_name" == "uv" ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv default install dir to PATH (current process only)
        if ! command_exists uv && [[ -x "$HOME/.local/bin/uv" ]]; then
          export PATH="$HOME/.local/bin:$PATH"
        fi
      else
        warn "Unknown tool: $tool_name"
      fi
      ;;
    *)
      warn "$tool_name not installed. Auto-install is not provided on this OS. Please install manually and retry."
      exit 1
      ;;
  esac

  if command_exists "$tool_name"; then
    success "$tool_name installed successfully"
  else
    error "$tool_name installation failed. Please install manually and retry."
    exit 1
  fi
}

compile() {
  # Backend deps
  if [[ -d "$PY_DIR" ]]; then
    info "Sync Python dependencies (uv sync)..."
    (cd "$PY_DIR" && bash scripts/prepare_envs.sh && uv run valuecell/server/db/init_db.py)
    success "Python dependencies synced"
  else
    warn "Backend directory not found: $PY_DIR. Skipping"
  fi

  # Frontend deps
  if [[ -d "$FRONTEND_DIR" ]]; then
    info "Install frontend dependencies (bun install)..."
    (cd "$FRONTEND_DIR" && bun install)
    success "Frontend dependencies installed"
  else
    warn "Frontend directory not found: $FRONTEND_DIR. Skipping"
  fi
}

start_backend() {
  if [[ ! -d "$PY_DIR" ]]; then
    warn "Backend directory not found; skipping backend start"
    return 0
  fi
  
  # Remove stale port file
  local port_file
  port_file="$(get_port_file_path)"
  rm -f "$port_file" 2>/dev/null || true
  
  info "Starting backend in debug mode (AGENT_DEBUG_MODE=true, API_PORT=auto)..."
  cd "$PY_DIR" && AGENT_DEBUG_MODE=true API_PORT=auto uv run python -m valuecell.server.main
}

start_frontend() {
  local backend_port="${1:-}"
  
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    warn "Frontend directory not found; skipping frontend start"
    return 0
  fi
  
  info "Starting frontend dev server (bun run dev)..."
  
  # If backend port is provided, set VITE_API_BASE_URL for the frontend
  if [[ -n "$backend_port" ]]; then
    info "Setting VITE_API_BASE_URL to http://localhost:$backend_port"
    export VITE_API_BASE_URL="http://localhost:$backend_port"
  fi
  
  (
    cd "$FRONTEND_DIR" && bun run dev
  ) & FRONTEND_PID=$!
  info "Frontend PID: $FRONTEND_PID"
}

cleanup() {
  echo
  info "Stopping services..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  success "Stopped"
}

trap cleanup EXIT INT TERM

print_usage() {
  cat <<'EOF'
Usage: ./start.sh [options]

Description:
  - Checks whether bun and uv are installed; on macOS, missing tools will be auto-installed via Homebrew.
  - Then installs backend and frontend dependencies and starts services.
  - Environment variables are loaded from system path:
    * macOS: ~/Library/Application Support/ValueCell/.env
    * Linux: ~/.config/valuecell/.env
    * Windows: %APPDATA%\ValueCell\.env
  - The .env file will be auto-created from .env.example on first run.
  - Debug mode is automatically enabled (AGENT_DEBUG_MODE=true) for local development.

Options:
  --no-frontend   Start backend only
  --no-backend    Start frontend only
  -h, --help      Show help
EOF
}

main() {
  local start_frontend_flag=1
  local start_backend_flag=1

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-frontend) start_frontend_flag=0; shift ;;
      --no-backend)  start_backend_flag=0; shift ;;
      -h|--help)     print_usage; exit 0 ;;
      *) error "Unknown argument: $1"; print_usage; exit 1 ;;
    esac
  done

  # Ensure tools
  ensure_tool bun oven-sh/bun/bun
  ensure_tool uv uv

  compile

  local backend_port=""

  # Start backend first (in background if frontend is also starting)
  if (( start_backend_flag )); then
    if (( start_frontend_flag )); then
      # Start backend in background and wait for port file
      (start_backend) &
      BACKEND_PID=$!
      
      # Wait for port file to appear
      backend_port=$(wait_for_port_file 30) || {
        error "Failed to start backend"
        exit 1
      }
    else
      # Only backend, run in foreground
      start_backend
    fi
  fi

  if (( start_frontend_flag )); then
    start_frontend "$backend_port"
  fi

  # Wait for background jobs
  wait
}

main "$@"