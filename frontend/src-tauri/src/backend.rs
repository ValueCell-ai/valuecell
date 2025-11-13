use anyhow::{bail, Context, Result};
use std::fs::create_dir_all;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::async_runtime::Receiver;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Backend process manager
pub struct BackendManager {
    processes: Mutex<Vec<CommandChild>>,
    backend_path: PathBuf,
    env_path: PathBuf,
    app: AppHandle,
}

impl BackendManager {
    fn wait_until_terminated(mut rx: Receiver<CommandEvent>) {
        while let Some(event) = rx.blocking_recv() {
            if matches!(event, CommandEvent::Terminated(_)) {
                break;
            }
        }
    }

    fn kill_descendants_best_effort(&self, parent_pid: u32) {
        // Try to kill all descendants of the given PID (macOS/Linux)
        // This is best-effort and ignores errors on platforms without `pkill`.
        let pid_str = parent_pid.to_string();

        for (signal, label) in [("-TERM", "graceful"), ("-KILL", "forceful")] {
            if let Ok((_rx, _child)) = self
                .app
                .shell()
                .command("pkill")
                .args([signal, "-P", &pid_str])
                .spawn()
            {
                log::info!(
                    "Issued {label} pkill ({signal}) for descendants of {}",
                    parent_pid
                );
            }

            // Allow graceful signal a moment to take effect before escalating.
            if signal == "-TERM" {
                std::thread::sleep(Duration::from_millis(150));
            }
        }
    }

    fn spawn_uv_module(&self, module_name: &str) -> Result<CommandChild> {
        log::info!(
            "Command: uv run --env-file {:?} -m {}",
            self.env_path,
            module_name
        );
        log::info!("Working directory: {:?}", self.backend_path);

        // Use sidecar command directly (Tauri handles platform automatically)
        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args([
                "run",
                "--env-file",
                self.env_path.to_str().context("Invalid env path")?,
                "-m",
                module_name,
            ])
            .current_dir(&self.backend_path);

        // Spawn and discard the receiver (we don't need to read output)
        let (_rx, child) = sidecar_command
            .spawn()
            .context(format!("Failed to spawn {}", module_name))?;

        log::info!("✓ {} spawned with PID: {}", module_name, child.pid());
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
            app,
        })
    }

    fn install_dependencies(&self) -> Result<()> {
        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args(["sync", "--frozen"])
            .current_dir(&self.backend_path);

        let (rx, _child) = sidecar_command.spawn().context("Failed to spawn uv sync")?;
        Self::wait_until_terminated(rx);

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

        // Run database initialization using sidecar command
        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args([
                "run",
                "--env-file",
                self.env_path.to_str().context("Invalid env path")?,
                init_db_script.to_str().context("Invalid script path")?,
            ])
            .current_dir(&self.backend_path);

        let (rx, _child) = sidecar_command
            .spawn()
            .context("Failed to run database initialization")?;
        Self::wait_until_terminated(rx);

        log::info!("✓ Database initialized");
        Ok(())
    }

    fn start_agent(&self, agent_name: &str) -> Result<CommandChild> {
        let module_name = match agent_name {
            "ResearchAgent" => "valuecell.agents.research_agent",
            "NewsAgent" => "valuecell.agents.news_agent",
            "StrategyAgent" => "valuecell.agents.strategy_agent",
            _ => bail!("Unknown agent: {}", agent_name),
        };

        let child = self.spawn_uv_module(&module_name)?;

        Ok(child)
    }

    fn start_backend_server(&self) -> Result<CommandChild> {
        self.spawn_uv_module("valuecell.server.main")
    }

    pub fn start_all(&self) -> Result<()> {
        self.install_dependencies()?;
        self.init_database()?;

        let mut processes = self.processes.lock().unwrap();

        let agents = vec!["ResearchAgent", "StrategyAgent", "NewsAgent"];
        for agent_name in agents {
            match self.start_agent(agent_name) {
                Ok(child) => {
                    log::info!("Process {} added to process list", child.pid());
                    processes.push(child);
                }
                Err(e) => log::error!("Failed to start {}: {}", agent_name, e),
            }
        }

        match self.start_backend_server() {
            Ok(child) => {
                log::info!("Process {} added to process list", child.pid());
                processes.push(child);
            }
            Err(e) => log::error!("Failed to start backend server: {}", e),
        }

        log::info!(
            "✓ All backend processes started (total: {})",
            processes.len()
        );

        // Note: CommandChild doesn't have try_wait, so we just log the count
        log::info!("Processes started: {}", processes.len());

        Ok(())
    }

    /// Stop all backend processes
    pub fn stop_all(&self) {
        log::info!("Stopping all backend processes...");

        let mut processes = self.processes.lock().unwrap();
        for process in processes.drain(..) {
            let pid = process.pid();
            log::info!("Terminating process {}", pid);

            // Attempt to terminate any descendants spawned under this process BEFORE killing the parent
            self.kill_descendants_best_effort(pid);

            // Use CommandChild's kill method
            if let Err(e) = process.kill() {
                log::error!("Failed to kill process {}: {}", pid, e);
            } else {
                log::info!("Process {} terminated", pid);
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
