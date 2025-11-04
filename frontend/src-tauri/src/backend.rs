use anyhow::{Context, Result};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

/// Backend process manager
pub struct BackendManager {
    processes: Mutex<Vec<Child>>,
    backend_path: PathBuf,
    env_path: PathBuf,
}

impl BackendManager {
    /// Create a new backend manager
    pub fn new(app: &AppHandle) -> Result<Self> {
        let resource_path = app
            .path()
            .resource_dir()
            .context("Failed to get resource directory")?;

        let backend_path = resource_path.join("backend");
        let env_path = backend_path.join(".env");

        log::info!("Backend path: {:?}", backend_path);
        log::info!("Env path: {:?}", env_path);

        Ok(Self {
            processes: Mutex::new(Vec::new()),
            backend_path,
            env_path,
        })
    }

    /// Check if .env file exists, if not, copy from template
    pub fn ensure_env_file(&self) -> Result<()> {
        if !self.env_path.exists() {
            log::info!(".env file not found, checking for template...");
            
            // .env.example is in Resources root (same level as backend/)
            let template_path = self.backend_path.parent()
                .ok_or_else(|| anyhow::anyhow!("Cannot get parent directory"))?
                .join(".env.example");
            
            if template_path.exists() {
                log::info!("Copying .env.example to .env at: {:?}", self.env_path);
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
        } else {
            log::info!("✓ .env file exists at: {:?}", self.env_path);
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
                log::info!("Found Python: {}", cmd);
                return Ok(cmd.to_string());
            }
        }
        
        Err(anyhow::anyhow!("Python not found. Please install Python 3.12+"))
    }

    /// Find or install uv
    fn find_uv(&self) -> Result<String> {
        // Try to find uv in system PATH
        if Command::new("uv")
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
        {
            log::info!("Found uv in system PATH");
            return Ok("uv".to_string());
        }

        log::warn!("uv not found in system PATH");
        Err(anyhow::anyhow!("uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/"))
    }

    /// Start a single agent
    fn start_agent(&self, agent_name: &str, uv_cmd: &str) -> Result<Child> {
        let command = match agent_name {
            "ResearchAgent" => {
                format!("cd {} && {} run --env-file {} -m valuecell.agents.research_agent", 
                    self.backend_path.display(), 
                    uv_cmd,
                    self.env_path.display())
            }
            "AutoTradingAgent" => {
                format!("cd {} && {} run --env-file {} -m valuecell.agents.auto_trading_agent", 
                    self.backend_path.display(), 
                    uv_cmd,
                    self.env_path.display())
            }
            "NewsAgent" => {
                format!("cd {} && {} run --env-file {} -m valuecell.agents.news_agent", 
                    self.backend_path.display(), 
                    uv_cmd,
                    self.env_path.display())
            }
            _ => return Err(anyhow::anyhow!("Unknown agent: {}", agent_name)),
        };

        log::info!("Starting {}: {}", agent_name, command);

        // Use sh -c to run the command string
        let child = Command::new("sh")
            .arg("-c")
            .arg(&command)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .context(format!("Failed to start {}", agent_name))?;

        log::info!("✓ {} started (PID: {})", agent_name, child.id());
        Ok(child)
    }

    /// Start backend server
    fn start_backend_server(&self, uv_cmd: &str) -> Result<Child> {
        let command = format!(
            "cd {} && {} run --env-file {} -m valuecell.server.main",
            self.backend_path.display(),
            uv_cmd,
            self.env_path.display()
        );

        log::info!("Starting backend server: {}", command);

        let child = Command::new("sh")
            .arg("-c")
            .arg(&command)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .context("Failed to start backend server")?;

        log::info!("✓ Backend server started (PID: {})", child.id());
        Ok(child)
    }

    /// Start all backend processes (agents + server)
    pub fn start_all(&self) -> Result<()> {
        log::info!("Starting ValueCell backend...");

        // Check Python
        self.find_python()?;

        // Check uv
        let uv_cmd = self.find_uv()?;

        // Ensure .env exists
        self.ensure_env_file()?;

        let mut processes = self.processes.lock().unwrap();

        // Start agents
        let agents = vec!["ResearchAgent", "AutoTradingAgent", "NewsAgent"];
        for agent_name in agents {
            match self.start_agent(agent_name, &uv_cmd) {
                Ok(child) => processes.push(child),
                Err(e) => log::error!("Failed to start {}: {}", agent_name, e),
            }
        }

        // Start backend server
        match self.start_backend_server(&uv_cmd) {
            Ok(child) => processes.push(child),
            Err(e) => log::error!("Failed to start backend server: {}", e),
        }

        log::info!("✓ All backend processes started");
        Ok(())
    }

    /// Stop all backend processes
    pub fn stop_all(&self) {
        log::info!("Stopping all backend processes...");
        
        let mut processes = self.processes.lock().unwrap();
        for mut process in processes.drain(..) {
            match process.kill() {
                Ok(_) => log::info!("✓ Process {} stopped", process.id()),
                Err(e) => log::error!("Failed to stop process {}: {}", process.id(), e),
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

