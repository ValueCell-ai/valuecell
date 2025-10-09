# PowerShell script to prepare Python environments
# Equivalent to prepare_envs.sh

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Highlight($message) {
    Write-Host $message -ForegroundColor Blue
}

function Write-Success($message) {
    Write-Host $message -ForegroundColor Green
}

function Write-Warn($message) {
    Write-Host $message -ForegroundColor Yellow
}

function Write-Err($message) {
    Write-Host $message -ForegroundColor Red
}

function Highlight-Command($command) {
    Write-Highlight "Running: $command"
}

# Check current directory and switch to python if needed
$currentPath = Get-Location
if ((Test-Path "python") -and (Test-Path "python\pyproject.toml") -and (Test-Path ".gitignore")) {
    Write-Warn "Detected project root. Switching to python directory..."
    Set-Location "python"
} elseif (-not (Test-Path "pyproject.toml") -or -not (Test-Path "third_party")) {
    Write-Err "Error: This script must be run from the project python directory or project root. You are in $currentPath"
    exit 1
}

# Final check if in python directory
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "third_party")) {
    Write-Err "Error: Failed to switch to python directory. You are in $(Get-Location)"
    exit 1
}

# Check if uv is installed
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Err "Error: 'uv' command not found. Please install 'uv' from https://docs.astral.sh/uv/"
    exit 1
}

Write-Highlight "=========================================="
Write-Highlight "Starting environment preparation..."
Write-Highlight "=========================================="

# Prepare main environment
Write-Success "Project root confirmed. Preparing environments..."

Write-Warn "Setting up main Python environment..."
if (-not (Test-Path ".venv")) {
    Highlight-Command "uv venv --python 3.12"
    uv venv --python 3.12
} else {
    Write-Warn ".venv already exists, skipping venv creation."
}
Highlight-Command "uv sync --group dev"
uv sync --group dev
Write-Success "Main environment setup complete."

Write-Highlight "=========================================="
Write-Highlight "Setting up third-party environments..."
Write-Highlight "=========================================="

# Setup ai-hedge-fund environment
Write-Warn "Setting up ai-hedge-fund environment..."
Push-Location ".\third_party\ai-hedge-fund"
try {
    if (-not (Test-Path ".venv")) {
        Highlight-Command "uv venv --python 3.12"
        uv venv --python 3.12
    } else {
        Write-Warn ".venv already exists, skipping venv creation."
    }
    Highlight-Command "uv sync"
    uv sync
    Write-Success "ai-hedge-fund environment setup complete."
} finally {
    Pop-Location
}

Write-Warn "------------------------------------------"
Write-Warn "Setting up TradingAgents environment..."
Write-Warn "------------------------------------------"

# Setup TradingAgents environment
Push-Location ".\third_party\TradingAgents"
try {
    if (-not (Test-Path ".venv")) {
        Highlight-Command "uv venv --python 3.12"
        uv venv --python 3.12
    } else {
        Write-Warn ".venv already exists, skipping venv creation."
    }
    Highlight-Command "uv sync"
    uv sync
    Write-Success "TradingAgents environment setup complete."
} finally {
    Pop-Location
}

Write-Success "=========================================="
Write-Success "All environments are set up."
Write-Success "=========================================="

