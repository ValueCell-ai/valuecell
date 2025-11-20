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
    if (-not (Test-Path $PY_DIR)) {
        Write-Warn "Backend directory not found; skipping backend start"
        return
    }
    
    Write-Info "Starting backend in debug mode (AGENT_DEBUG_MODE=true)..."
    Push-Location $PY_DIR
    try {
        # Set debug mode for local development
        $env:AGENT_DEBUG_MODE = "true"
        & uv run python -m valuecell.server.main
    } catch {
        Write-Err "Failed to start backend: $_"
    } finally {
        Pop-Location
    }
}

function Start-Frontend {
    if (-not (Test-Path $FRONTEND_DIR)) {
        Write-Warn "Frontend directory not found; skipping frontend start"
        return
    }
    
    Write-Info "Starting frontend dev server (bun run dev)..."
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

    # Start services based on flags
    if (-not $NoFrontend) {
        Start-Frontend
        Start-Sleep -Seconds 5  # Give frontend a moment to start
    }

    if (-not $NoBackend) {
        Start-Backend
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

