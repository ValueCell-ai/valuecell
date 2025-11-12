use anyhow::{bail, Context, Result};
use std::fs::{create_dir_all, File};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};

/// Backend process manager
pub struct BackendManager {
    processes: Mutex<Vec<Child>>,
    backend_path: PathBuf,
    env_path: PathBuf,
    log_dir: PathBuf,
}

impl BackendManager {
    fn spawn_uv_module(&self, module_name: &str, log_name: &str) -> Result<Child> {
        let log_file = self
            .log_dir
            .join(format!("{}.log", log_name.replace(' ', "_")));
        let stdout_file = File::create(&log_file)
            .with_context(|| format!("Failed to create log file for {}", log_name))?;
        let stderr_file = stdout_file
            .try_clone()
            .context("Failed to clone log file handle")?;

        log::info!("Starting {} with log file: {:?}", log_name, log_file);
        log::info!(
            "Command: {} run --env-file {:?} -m {}",
            "uv",
            self.env_path,
            module_name
        );
        log::info!("Working directory: {:?}", self.backend_path);

        let child = Command::new("uv")
            .arg("run")
            .arg("--env-file")
            .arg(&self.env_path)
            .arg("-m")
            .arg(module_name)
            .current_dir(&self.backend_path)
            .stdout(Stdio::from(stdout_file))
            .stderr(Stdio::from(stderr_file))
            .spawn()
            .with_context(|| format!("Failed to spawn {}", log_name))?;

        log::info!("✓ {} spawned with PID: {}", log_name, child.id());
        Ok(child)
    }

    pub fn new(app: AppHandle) -> Result<Self> {
        let resource_root = app
            .path()
            .resolve(".", BaseDirectory::Resource)
            .context("Failed to resolve resource root")?;

        let backend_path = if resource_root.join("backend").exists() {
            resource_root.join("backend")
        } else {
            let project_root = resource_root
                .ancestors()
                .find(|dir| {
                    let python_dir = dir.join("python");
                    log::info!(
                        "Checking directory: {:?}, exists python dir: {:?}",
                        dir,
                        python_dir.exists()
                    );
                    python_dir.exists()
                })
                .context("Could not find project root (looking for python directory)")?;

            project_root.to_path_buf().join("python")
        };

        let env_path = backend_path
            .parent()
            .context("Failed to get parent directory")?
            .join(".env");

        if !env_path.exists() {
            return Err(anyhow::anyhow!("Env file does not exist: {:?}", env_path));
        }

        // Create log directory in app's log directory
        let log_dir = app
            .path()
            .app_log_dir()
            .context("Failed to get log directory")?
            .join("backend");

        create_dir_all(&log_dir).context("Failed to create log directory")?;

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

    fn find_uv(&self) -> Result<()> {
        if Command::new("uv")
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
        {
            return Ok(());
        }
        Err(anyhow::anyhow!(
            "uv not found on PATH. Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        ))
    }

    fn install_dependencies(&self) -> Result<()> {
        let status = Command::new("uv")
            .arg("sync")
            .arg("--frozen")
            .current_dir(&self.backend_path)
            .status()
            .context("Failed to install dependencies")?;

        if !status.success() {
            return Err(anyhow::anyhow!("Failed to sync dependencies"));
        }

        log::info!("✓ Dependencies installed/verified");
        Ok(())
    }

    fn init_database(&self) -> Result<()> {
        let init_db_script = self.backend_path.join("valuecell/server/db/init_db.py");

        // Check if init_db.py exists
        if !init_db_script.exists() {
            log::warn!("Database init script not found at: {:?}", init_db_script);
            return Ok(());
        }

        // Run database initialization and surface output directly
        let status = Command::new("uv")
            .arg("run")
            .arg("--env-file")
            .arg(&self.env_path)
            .arg(&init_db_script)
            .current_dir(&self.backend_path)
            .status()
            .context("Failed to run database initialization")?;

        if !status.success() {
            return Err(anyhow::anyhow!("Database initialization had warnings"));
        }

        log::info!("✓ Database initialized");
        Ok(())
    }

    fn start_agent(&self, agent_name: &str) -> Result<Child> {
        let module_name = match agent_name {
            "ResearchAgent" => "valuecell.agents.research_agent",
            "AutoTradingAgent" => "valuecell.agents.auto_trading_agent",
            "NewsAgent" => "valuecell.agents.news_agent",
            _ => bail!("Unknown agent: {}", agent_name),
        };

        let child = self.spawn_uv_module(module_name, agent_name)?;

        std::thread::sleep(std::time::Duration::from_millis(500));

        Ok(child)
    }

    fn start_backend_server(&self) -> Result<Child> {
        self.spawn_uv_module("valuecell.server.main", "backend_server")
    }

    pub fn start_all(&self) -> Result<()> {
        self.find_uv()?;
        self.install_dependencies()?;
        self.init_database()?;

        let mut processes = self.processes.lock().unwrap();

        let agents = vec!["ResearchAgent", "AutoTradingAgent", "NewsAgent"];
        for agent_name in agents {
            match self.start_agent(agent_name) {
                Ok(child) => {
                    log::info!("Process {} added to process list", child.id());
                    processes.push(child);
                }
                Err(e) => log::error!("Failed to start {}: {}", agent_name, e),
            }
        }

        match self.start_backend_server() {
            Ok(child) => {
                log::info!("Process {} added to process list", child.id());
                processes.push(child);
            }
            Err(e) => log::error!("Failed to start backend server: {}", e),
        }

        log::info!(
            "✓ All backend processes started (total: {})",
            processes.len()
        );

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
            let pid = process.id();
            log::info!("Terminating process {}", pid);

            // First try graceful termination with SIGTERM
            #[cfg(unix)]
            {
                use std::process::Command as SysCommand;
                let _ = SysCommand::new("kill")
                    .arg("-TERM")
                    .arg(pid.to_string())
                    .output();

                // Wait a bit for graceful shutdown
                std::thread::sleep(std::time::Duration::from_millis(500));

                // Check if process is still alive
                match process.try_wait() {
                    Ok(None) => {
                        // Process still running, force kill
                        log::warn!("Process {} did not terminate gracefully, forcing kill", pid);
                        if let Err(e) = process.kill() {
                            log::error!("Failed to force kill process {}: {}", pid, e);
                        }
                    }
                    Ok(Some(status)) => {
                        log::info!("Process {} terminated with status: {:?}", pid, status);
                    }
                    Err(e) => {
                        log::error!("Error checking process {} status: {}", pid, e);
                    }
                }
            }

            #[cfg(not(unix))]
            {
                if let Err(e) = process.kill() {
                    log::error!("Failed to stop process {}: {}", pid, e);
                }
            }

            // Wait for the process to fully exit
            let _ = process.wait();
        }

        log::info!("✓ All backend processes stopped");
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}
