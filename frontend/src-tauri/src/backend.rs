use anyhow::{Context, Result};
use std::fs::{File, create_dir_all};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

/// Backend process manager
pub struct BackendManager {
    processes: Mutex<Vec<Child>>,
    backend_path: PathBuf,
    env_path: PathBuf,
    log_dir: PathBuf,
}

impl BackendManager {
    /// Create a new backend manager
    pub fn new(app: &AppHandle) -> Result<Self> {
        // In development mode, use the actual project's python directory
        // In production, use the bundled backend directory
        let backend_path = if cfg!(debug_assertions) {
            // Development mode: find project root by looking for pyproject.toml
            let exe_path = std::env::current_exe()
                .context("Failed to get executable path")?;
            
            log::info!("Executable path: {:?}", exe_path);
            
            // Start from exe and walk up to find project root (has python/ directory and .env.example)
            let mut current = exe_path.parent();
            let mut project_root = None;
            
            while let Some(dir) = current {
                let python_dir = dir.join("python");
                let pyproject = python_dir.join("pyproject.toml");
                
                log::info!("Checking directory: {:?}", dir);
                log::info!("  Python dir exists: {}", python_dir.exists());
                log::info!("  pyproject.toml exists: {}", pyproject.exists());
                
                if python_dir.exists() && pyproject.exists() {
                    project_root = Some(dir);
                    break;
                }
                current = dir.parent();
            }
            
            let project_root = project_root
                .context("Could not find project root (looking for python/pyproject.toml)")?;
            
            log::info!("Found project root: {:?}", project_root);
            project_root.join("python")
        } else {
            // Production mode: use bundled backend
            let resource_path = app
                .path()
                .resource_dir()
                .context("Failed to get resource directory")?;
            resource_path.join("backend")
        };

        let env_path = if cfg!(debug_assertions) {
            // Development: .env is in project root
            backend_path.parent()
                .context("Failed to get parent directory")?
                .join(".env")
        } else {
            // Production: .env is in backend directory
            backend_path.join(".env")
        };
        
        // Create log directory in app's log directory
        let log_dir = app
            .path()
            .app_log_dir()
            .context("Failed to get log directory")?
            .join("backend");
        
        create_dir_all(&log_dir)
            .context("Failed to create log directory")?;

        log::info!("Mode: {}", if cfg!(debug_assertions) { "Development" } else { "Production" });
        log::info!("Backend path: {:?}", backend_path);
        log::info!("Env path: {:?}", env_path);
        log::info!("Log directory: {:?}", log_dir);

        Ok(Self {
            processes: Mutex::new(Vec::new()),
            backend_path,
            env_path,
            log_dir,
        })
    }

    /// Check if .env file exists, if not, copy from template
    pub fn ensure_env_file(&self) -> Result<()> {
        if !self.env_path.exists() {
            // .env.example is in Resources root (same level as backend/)
            let template_path = self.backend_path.parent()
                .ok_or_else(|| anyhow::anyhow!("Cannot get parent directory"))?
                .join(".env.example");
            
            if template_path.exists() {
                std::fs::copy(&template_path, &self.env_path)
                    .context("Failed to copy .env.example template")?;
                
                log::warn!("═══════════════════════════════════════════════");
                log::warn!("⚠️  IMPORTANT: Please configure your .env file");
                log::warn!("📁 Location: {:?}", self.env_path);
                log::warn!("🔑 Add your API keys (OPENAI_API_KEY, etc.)");
                log::warn!("🔄 Restart the application after configuration");
                log::warn!("═══════════════════════════════════════════════");
            } else {
                log::error!("❌ .env.example template not found at: {:?}", template_path);
                log::error!("Please create a .env file manually at: {:?}", self.env_path);
            }
        }
        Ok(())
    }

    /// Find Python interpreter (system Python or bundled)
    fn find_python(&self) -> Result<String> {
        // For now, use system Python
        // In the future, we could bundle Python with the app
        
        // Try common Python commands
        let python_commands = vec!["python3", "python"];
        
        for cmd in python_commands {
            if Command::new(cmd)
                .arg("--version")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .is_ok()
            {
                return Ok(cmd.to_string());
            }
        }
        
        Err(anyhow::anyhow!("Python not found. Please install Python 3.12+"))
    }

    /// Find or install uv
    fn find_uv(&self) -> Result<String> {
        // Common uv installation paths (with ~ for home directory)
        let uv_paths = vec![
            "uv",  // Try PATH first
            "~/.local/bin/uv",  // uv default install location (Linux/macOS)
            "/usr/local/bin/uv",
            "~/.cargo/bin/uv",  // Cargo install location
        ];

        let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());

        for uv_cmd in &uv_paths {
            // Expand ~ to home directory
            let expanded_path = uv_cmd.replace("~", &home);

            if Command::new(&expanded_path)
                .arg("--version")
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .is_ok()
            {
                log::info!("Found uv at: {}", expanded_path);
                return Ok(expanded_path);
            }
        }

        Err(anyhow::anyhow!("uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/\nSearched paths: {:?}", uv_paths))
    }

    /// Start a single agent
    fn start_agent(&self, agent_name: &str, uv_cmd: &str) -> Result<Child> {
        let module_name = match agent_name {
            "ResearchAgent" => "valuecell.agents.research_agent",
            "AutoTradingAgent" => "valuecell.agents.auto_trading_agent",
            "NewsAgent" => "valuecell.agents.news_agent",
            _ => return Err(anyhow::anyhow!("Unknown agent: {}", agent_name)),
        };

        // Verify backend path exists
        if !self.backend_path.exists() {
            return Err(anyhow::anyhow!(
                "Backend path does not exist: {:?}", 
                self.backend_path
            ));
        }

        // Verify env file exists
        if !self.env_path.exists() {
            return Err(anyhow::anyhow!(
                "Env file does not exist: {:?}", 
                self.env_path
            ));
        }

        // Create log files for stdout and stderr
        let log_file = self.log_dir.join(format!("{}.log", agent_name));
        let stdout_file = File::create(&log_file)
            .context(format!("Failed to create log file for {}", agent_name))?;
        let stderr_file = stdout_file.try_clone()
            .context("Failed to clone log file handle")?;

        log::info!("Starting {} with log file: {:?}", agent_name, log_file);
        log::info!("Command: {} run --env-file {:?} -m {}", uv_cmd, self.env_path, module_name);
        log::info!("Working directory: {:?}", self.backend_path);

        // First, test if the command works by doing a dry run
        log::info!("Testing command availability...");
        let test_result = Command::new(uv_cmd)
            .arg("--version")
            .output();
        
        match test_result {
            Ok(output) => {
                log::info!("UV version check: {:?}", String::from_utf8_lossy(&output.stdout));
            }
            Err(e) => {
                log::error!("UV command test failed: {}", e);
            }
        }

        // Run agent in backend directory (python/)
        let mut command = Command::new(uv_cmd);
        command
            .arg("run")
            .arg("--env-file")
            .arg(&self.env_path)
            .arg("-m")
            .arg(module_name)
            .current_dir(&self.backend_path)
            .stdout(Stdio::from(stdout_file))
            .stderr(Stdio::from(stderr_file));

        log::info!("Spawning process...");
        let child = command.spawn()
            .context(format!("Failed to spawn {}", agent_name))?;

        let pid = child.id();
        log::info!("✓ {} spawned with PID: {}", agent_name, pid);
        
        // Wait a moment to see if the process exits immediately
        std::thread::sleep(std::time::Duration::from_millis(500));
        
        Ok(child)
    }

    /// Start backend server
    fn start_backend_server(&self, uv_cmd: &str) -> Result<Child> {
        // Create log files for stdout and stderr
        let log_file = self.log_dir.join("backend_server.log");
        let stdout_file = File::create(&log_file)
            .context("Failed to create log file for backend server")?;
        let stderr_file = stdout_file.try_clone()
            .context("Failed to clone log file handle")?;

        log::info!("Starting backend server with log file: {:?}", log_file);
        log::info!("Command: {} run --env-file {:?} -m valuecell.server.main", uv_cmd, self.env_path);
        log::info!("Working directory: {:?}", self.backend_path);

        // Run backend server in backend directory (python/)
        let child = Command::new(uv_cmd)
            .arg("run")
            .arg("--env-file")
            .arg(&self.env_path)
            .arg("-m")
            .arg("valuecell.server.main")
            .current_dir(&self.backend_path)
            .stdout(Stdio::from(stdout_file))
            .stderr(Stdio::from(stderr_file))
            .spawn()
            .context("Failed to start backend server")?;

        log::info!("✓ Backend server started with PID: {}", child.id());
        Ok(child)
    }

    /// Install dependencies using uv sync
    fn install_dependencies(&self, uv_cmd: &str) -> Result<()> {
        log::info!("Checking Python dependencies...");
        
        // Run uv sync to install dependencies
        let output = Command::new(uv_cmd)
            .arg("sync")
            .arg("--frozen")  // Use exact versions from uv.lock
            .current_dir(&self.backend_path)
            .output()
            .context("Failed to run uv sync")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            log::error!("uv sync failed: {}", stderr);
            return Err(anyhow::anyhow!("Failed to sync dependencies: {}", stderr));
        }

        log::info!("✓ Dependencies installed/verified");
        Ok(())
    }

    /// Initialize database
    fn init_database(&self, uv_cmd: &str) -> Result<()> {
        log::info!("Initializing database...");
        
        let init_db_script = self.backend_path.join("valuecell/server/db/init_db.py");
        
        // Check if init_db.py exists
        if !init_db_script.exists() {
            log::warn!("Database init script not found at: {:?}", init_db_script);
            log::warn!("Skipping database initialization");
            return Ok(());
        }

        // Run database initialization
        let output = Command::new(uv_cmd)
            .arg("run")
            .arg("--env-file")
            .arg(&self.env_path)
            .arg(&init_db_script)
            .current_dir(&self.backend_path)
            .output()
            .context("Failed to run database initialization")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let stdout = String::from_utf8_lossy(&output.stdout);
            log::warn!("Database initialization output: {}", stdout);
            log::warn!("Database initialization stderr: {}", stderr);
            // Don't fail if database already initialized
            log::warn!("Database initialization had warnings, but continuing...");
        } else {
            log::info!("✓ Database initialized");
        }

        Ok(())
    }

    /// Start all backend processes (agents + server)
    pub fn start_all(&self) -> Result<()> {
        log::info!("Starting ValueCell backend...");
        log::info!("📁 Backend logs will be saved to: {:?}", self.log_dir);

        // Check Python
        self.find_python()?;

        // Check uv
        let uv_cmd = self.find_uv()?;
        log::info!("Found uv: {}", uv_cmd);

        // Ensure .env exists
        self.ensure_env_file()?;

        // Install dependencies if not already installed
        self.install_dependencies(&uv_cmd)?;

        // Initialize database
        self.init_database(&uv_cmd)?;

        let mut processes = self.processes.lock().unwrap();

        // Start agents
        let agents = vec!["ResearchAgent", "AutoTradingAgent", "NewsAgent"];
        for agent_name in agents {
            match self.start_agent(agent_name, &uv_cmd) {
                Ok(child) => {
                    log::info!("Process {} added to process list", child.id());
                    processes.push(child);
                }
                Err(e) => log::error!("Failed to start {}: {}", agent_name, e),
            }
        }

        // Start backend server
        match self.start_backend_server(&uv_cmd) {
            Ok(child) => {
                log::info!("Process {} added to process list", child.id());
                processes.push(child);
            }
            Err(e) => log::error!("Failed to start backend server: {}", e),
        }

        log::info!("✓ All backend processes started (total: {})", processes.len());
        
        // Check if processes are still alive after a short delay
        std::thread::sleep(std::time::Duration::from_secs(1));
        
        let mut alive_count = 0;
        for process in processes.iter_mut() {
            match process.try_wait() {
                Ok(None) => {
                    // Process is still running
                    alive_count += 1;
                }
                Ok(Some(status)) => {
                    log::warn!("Process {} exited with status: {:?}", process.id(), status);
                }
                Err(e) => {
                    log::error!("Error checking process status: {}", e);
                }
            }
        }
        
        log::info!("Processes still alive: {}/{}", alive_count, processes.len());
        
        if alive_count == 0 && processes.len() > 0 {
            log::error!("⚠️  All processes exited immediately! Check log files for errors.");
        }
        
        Ok(())
    }

    /// Stop all backend processes
    pub fn stop_all(&self) {
        log::info!("Stopping all backend processes...");
        
        let mut processes = self.processes.lock().unwrap();
        for mut process in processes.drain(..) {
            if let Err(e) = process.kill() {
                log::error!("Failed to stop process {}: {}", process.id(), e);
            }
        }
        
        log::info!("✓ All backend processes stopped");
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}

