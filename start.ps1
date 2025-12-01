# Simple project launcher with auto-install for bun and uv
# - Windows: uses PowerShell installation scripts
# - Supports --no-frontend, --no-backend, -h/--help options

param(
    [switch]$NoFrontend,
    [switch]$NoBackend,
    [Alias("h")]
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$FRONTEND_DIR = Join-Path $SCRIPT_DIR "frontend"
$PY_DIR = Join-Path $SCRIPT_DIR "python"

$BACKEND_PROCESS = $null
$FRONTEND_PROCESS = $null

# Port file name (must match Python's PORT_FILE_NAME)
$PORT_FILE_NAME = "backend.port"

# Get system config directory (must match Python's get_system_env_dir)
function Get-SystemConfigDir {
    $appData = $env:APPDATA
    if ($appData) {
        return Join-Path $appData "ValueCell"
    }
    return Join-Path $env:USERPROFILE "AppData\Roaming\ValueCell"
}

# Get port file path
function Get-PortFilePath {
    return Join-Path (Get-SystemConfigDir) $PORT_FILE_NAME
}

# Read backend port from port file
function Read-BackendPort {
    $portFile = Get-PortFilePath
    if (Test-Path $portFile) {
        $content = Get-Content $portFile -Raw -ErrorAction SilentlyContinue
        if ($content) {
            return $content.Trim()
        }
    }
    return $null
}

# Wait for port file and return the port
function Wait-ForPortFile {
    param(
        [int]$TimeoutSeconds = 30
    )
    
    $portFile = Get-PortFilePath
    $elapsed = 0
    
    Write-Info "Waiting for backend port file..."
    
    while ((-not (Test-Path $portFile)) -and ($elapsed -lt $TimeoutSeconds)) {
        Start-Sleep -Milliseconds 500
        $elapsed++
    }
    
    if (Test-Path $portFile) {
        $port = Get-Content $portFile -Raw -ErrorAction SilentlyContinue
        if ($port) {
            $port = $port.Trim()
            Write-Success "Backend started on port: $port"
            return $port
        }
    }
    
    Write-Err "Timeout waiting for backend port file"
    return $null
}

# Color output functions
function Write-Info($message) {
    Write-Host "[INFO]  $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "[ OK ]  $message" -ForegroundColor Green
}

function Write-Warn($message) {
    Write-Host "[WARN]  $message" -ForegroundColor Yellow
}

function Write-Err($message) {
    Write-Host "[ERR ]  $message" -ForegroundColor Red
}

function Test-CommandExists($command) {
    $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

function Ensure-Tool($toolName) {
    if (Test-CommandExists $toolName) {
        try {
            $version = & $toolName --version 2>$null | Select-Object -First 1
            if (-not $version) { $version = "version unknown" }
            Write-Success "$toolName is installed ($version)"
        } catch {
            Write-Success "$toolName is installed"
        }
        return
    }

    Write-Info "Installing $toolName..."
    
    if ($toolName -eq "bun") {
        # Install bun on Windows using PowerShell script
        try {
            Write-Info "Installing bun via PowerShell script..."
            # Use a new PowerShell process to avoid variable conflicts
            $installCmd = "irm https://bun.sh/install.ps1 | iex"
            powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $installCmd
            
            # Add to PATH for current session
            $bunPath = "$env:USERPROFILE\.bun\bin"
            if (Test-Path $bunPath) {
                $env:Path = "$bunPath;$env:Path"
            }
        } catch {
            Write-Err "Failed to install bun: $_"
            Write-Err "Please install manually from https://bun.sh/docs/installation"
            exit 1
        }
    } elseif ($toolName -eq "uv") {
        # Install uv on Windows using PowerShell script
        try {
            Write-Info "Installing uv via PowerShell script..."
            # Use a new PowerShell process to avoid variable conflicts
            $installCmd = "irm https://astral.sh/uv/install.ps1 | iex"
            powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $installCmd
            
            # Add to PATH for current session - check multiple possible locations
            $possiblePaths = @(
                "$env:USERPROFILE\.cargo\bin",
                "$env:USERPROFILE\.local\bin",
                "$env:LOCALAPPDATA\Programs\uv"
            )
            foreach ($uvPath in $possiblePaths) {
                if (Test-Path $uvPath) {
                    $env:Path = "$uvPath;$env:Path"
                    break
                }
            }
        } catch {
            Write-Err "Failed to install uv: $_"
            Write-Err "Please install manually from https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        }
    } else {
        Write-Warn "Unknown tool: $toolName"
        exit 1
    }

    # Verify installation
    if (Test-CommandExists $toolName) {
        Write-Success "$toolName installed successfully"
    } else {
        Write-Err "$toolName installation failed. Please install manually and retry."
        Write-Err "You may need to restart your terminal or add the tool to your PATH."
        exit 1
    }
}

function Compile {
    # Backend deps
    if (Test-Path $PY_DIR) {
        Write-Info "Sync Python dependencies (uv sync)..."
        Push-Location $PY_DIR
        try {
            # Run prepare environments script
            if (Test-Path "scripts\prepare_envs.ps1") {
                Write-Info "Running environment preparation script..."
                & ".\scripts\prepare_envs.ps1"
            } else {
                Write-Warn "prepare_envs.ps1 not found, running uv sync directly..."
                uv sync
            }
            uv run valuecell/server/db/init_db.py
            Write-Success "Python dependencies synced"
        } catch {
            Write-Err "Failed to sync Python dependencies: $_"
            exit 1
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "Backend directory not found: $PY_DIR. Skipping"
    }

    # Frontend deps
    if (Test-Path $FRONTEND_DIR) {
        Write-Info "Install frontend dependencies (bun install)..."
        Push-Location $FRONTEND_DIR
        try {
            bun install
            Write-Success "Frontend dependencies installed"
        } catch {
            Write-Err "Failed to install frontend dependencies: $_"
            exit 1
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "Frontend directory not found: $FRONTEND_DIR. Skipping"
    }
}

function Start-Backend {
    param(
        [switch]$AsJob
    )
    
    if (-not (Test-Path $PY_DIR)) {
        Write-Warn "Backend directory not found; skipping backend start"
        return
    }
    
    # Remove stale port file
    $portFile = Get-PortFilePath
    if (Test-Path $portFile) {
        Remove-Item $portFile -Force -ErrorAction SilentlyContinue
    }
    
    Write-Info "Starting backend in debug mode (AGENT_DEBUG_MODE=true, API_PORT=auto)..."
    
    if ($AsJob) {
        # Start as background job
        $script:BACKEND_PROCESS = Start-Process -FilePath "uv" `
            -ArgumentList "run", "python", "-m", "valuecell.server.main" `
            -WorkingDirectory $PY_DIR `
            -NoNewWindow -PassThru `
            -Environment @{
                "AGENT_DEBUG_MODE" = "true"
                "API_PORT" = "auto"
            }
        Write-Info "Backend PID: $($script:BACKEND_PROCESS.Id)"
    } else {
        Push-Location $PY_DIR
        try {
            # Set debug mode and auto port for local development
            $env:AGENT_DEBUG_MODE = "true"
            $env:API_PORT = "auto"
            & uv run python -m valuecell.server.main
        } catch {
            Write-Err "Failed to start backend: $_"
        } finally {
            Pop-Location
        }
    }
}

function Start-Frontend {
    param(
        [string]$BackendPort
    )
    
    if (-not (Test-Path $FRONTEND_DIR)) {
        Write-Warn "Frontend directory not found; skipping frontend start"
        return
    }
    
    Write-Info "Starting frontend dev server (bun run dev)..."
    
    # If backend port is provided, set VITE_API_BASE_URL for the frontend
    if ($BackendPort) {
        Write-Info "Setting VITE_API_BASE_URL to http://localhost:$BackendPort"
        $env:VITE_API_BASE_URL = "http://localhost:$BackendPort"
    }
    
    Push-Location $FRONTEND_DIR
    try {
        # Try to find the actual bun.exe first
        $bunExe = "$env:USERPROFILE\.bun\bin\bun.exe"
        $bunPath = $null
        
        if (Test-Path $bunExe) {
            $bunPath = $bunExe
            Write-Info "Using bun at: $bunPath"
            $script:FRONTEND_PROCESS = Start-Process -FilePath $bunPath -ArgumentList "run", "dev" -NoNewWindow -PassThru
        } else {
            # Fallback: get command and handle .ps1 scripts
            $bunCmd = Get-Command "bun" -ErrorAction Stop
            $resolvedPath = $bunCmd.Source
            
            if ([System.IO.Path]::GetExtension($resolvedPath) -eq ".ps1") {
                # If it's a PowerShell script, use powershell.exe to execute it
                Write-Info "Using bun script at: $resolvedPath"
                $currentDir = Get-Location
                $script:FRONTEND_PROCESS = Start-Process -FilePath "powershell.exe" `
                    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "& { Set-Location '$currentDir'; & '$resolvedPath' run dev }" `
                    -NoNewWindow -PassThru
            } else {
                # Regular executable
                Write-Info "Using bun at: $resolvedPath"
                $script:FRONTEND_PROCESS = Start-Process -FilePath $resolvedPath -ArgumentList "run", "dev" -NoNewWindow -PassThru
            }
        }
        
        Write-Info "Frontend PID: $($script:FRONTEND_PROCESS.Id)"
    } catch {
        Write-Err "Failed to start frontend: $_"
        throw
    } finally {
        Pop-Location
    }
}

function Cleanup {
    Write-Host ""
    Write-Info "Stopping services..."
    
    if ($script:FRONTEND_PROCESS -and -not $script:FRONTEND_PROCESS.HasExited) {
        try {
            Stop-Process -Id $script:FRONTEND_PROCESS.Id -Force -ErrorAction SilentlyContinue
        } catch {
            # Ignore errors
        }
    }
    
    if ($script:BACKEND_PROCESS -and -not $script:BACKEND_PROCESS.HasExited) {
        try {
            Stop-Process -Id $script:BACKEND_PROCESS.Id -Force -ErrorAction SilentlyContinue
        } catch {
            # Ignore errors
        }
    }
    
    Write-Success "Stopped"
}

function Print-Usage {
    Write-Host @"
Usage: .\start.ps1 [options]

Description:
  - Checks whether bun and uv are installed; missing tools will be auto-installed via PowerShell scripts.
  - Then installs backend and frontend dependencies and starts services.
  - Environment variables are loaded from system path:
    * macOS: ~/Library/Application Support/ValueCell/.env
    * Linux: ~/.config/valuecell/.env
    * Windows: %APPDATA%\ValueCell\.env
  - The .env file will be auto-created from .env.example on first run.
  - Debug mode is automatically enabled (AGENT_DEBUG_MODE=true) for local development.

Options:
  -NoFrontend     Start backend only
  -NoBackend      Start frontend only
  -Help, -h       Show this help message
"@
}

# Handle Ctrl+C and cleanup
Register-EngineEvent PowerShell.Exiting -Action { Cleanup } | Out-Null
try {
    # Show help if requested
    if ($Help) {
        Print-Usage
        exit 0
    }

    # Ensure tools are installed
    Ensure-Tool "bun"
    Ensure-Tool "uv"

    # Compile/install dependencies
    Compile

    $backendPort = $null

    # Start backend first (in background if frontend is also starting)
    if (-not $NoBackend) {
        if (-not $NoFrontend) {
            # Start backend in background and wait for port file
            Start-Backend -AsJob
            Start-Sleep -Seconds 2  # Give backend a moment to start writing port file
            
            # Wait for port file to appear
            $backendPort = Wait-ForPortFile -TimeoutSeconds 30
            if (-not $backendPort) {
                Write-Err "Failed to start backend"
                exit 1
            }
        } else {
            # Only backend, run in foreground
            Start-Backend
        }
    }

    # Start frontend with discovered backend port
    if (-not $NoFrontend) {
        Start-Frontend -BackendPort $backendPort
        Start-Sleep -Seconds 5  # Give frontend a moment to start
    }

    # If frontend is running, wait for it
    if ($script:FRONTEND_PROCESS -and -not $script:FRONTEND_PROCESS.HasExited) {
        Write-Info "Services running. Press Ctrl+C to stop..."
        Wait-Process -Id $script:FRONTEND_PROCESS.Id -ErrorAction SilentlyContinue
    }
} catch {
    Write-Err "An error occurred: $_"
    exit 1
} finally {
    Cleanup
}

