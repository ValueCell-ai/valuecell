use anyhow::{Context, Result};
use std::fs::{create_dir_all, OpenOptions};
use std::io::Write;
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
    log_dir: PathBuf,
    app: AppHandle,
}

const MAIN_MODULE: &str = "valuecell.server.main";
const INIT_DB_MODULE: &str = "valuecell.server.db.init_db";

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
        let (rx, child) = self.spawn_uv_command(module_name)?;
        self.handle_process_output(module_name, rx);
        log::info!("✓ {} spawned with PID: {}", module_name, child.pid());
        Ok(child)
    }

    fn spawn_uv_command(
        &self,
        module_name: &str,
    ) -> Result<(Receiver<CommandEvent>, CommandChild)> {
        log::info!("Command: uv run -m {}", module_name);

        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args(["run", "-m", module_name])
            .current_dir(&self.backend_path);

        sidecar_command
            .spawn()
            .context(format!("Failed to spawn {}", module_name))
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

        let log_dir = app
            .path()
            .app_log_dir()
            .context("Failed to get log directory")?
            .join("backend");

        create_dir_all(&log_dir).context("Failed to create log directory")?;

        log::info!("Backend path: {:?}", backend_path);
        log::info!("Log directory: {:?}", log_dir);

        Ok(Self {
            processes: Mutex::new(Vec::new()),
            backend_path,
            log_dir,
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
        log::info!("Running blocking module: {}", INIT_DB_MODULE);
        let (rx, _child) = self.spawn_uv_command(INIT_DB_MODULE)?;
        Self::wait_until_terminated(rx);
        log::info!("✓ {} completed", INIT_DB_MODULE);
        Ok(())
    }

    pub fn start_all(&self) -> Result<()> {
        self.install_dependencies()?;
        self.init_database()?;

        let mut processes = self.processes.lock().unwrap();

        match self.spawn_uv_module(MAIN_MODULE) {
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

    fn handle_process_output(&self, module_name: &str, rx: Receiver<CommandEvent>) {
        if module_name != MAIN_MODULE {
            Self::wait_until_terminated(rx);
            return;
        }

        let log_path = self.log_dir.join("backend.log");
        std::thread::spawn(move || Self::stream_to_file(rx, log_path));
    }

    fn stream_to_file(mut rx: Receiver<CommandEvent>, log_path: PathBuf) {
        let mut file = match OpenOptions::new().create(true).append(true).open(&log_path) {
            Ok(file) => file,
            Err(err) => {
                log::error!("Failed to open backend log file {:?}: {}", log_path, err);
                return;
            }
        };

        while let Some(event) = rx.blocking_recv() {
            match event {
                CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                    let text = String::from_utf8_lossy(&line);
                    if let Err(err) = writeln!(file, "{}", text.trim_end_matches('\n')) {
                        log::error!("Failed to write backend log line: {}", err);
                        break;
                    }
                }
                CommandEvent::Error(err) => {
                    log::error!("Backend process error: {}", err);
                    break;
                }
                CommandEvent::Terminated(_) => break,
                _ => {}
            }
        }
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}
