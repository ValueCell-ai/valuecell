use anyhow::{anyhow, Context, Result};
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
        // First, send SIGINT (Ctrl+C equivalent) and wait up to 5 seconds.
        // If processes are still running, escalate to SIGKILL.
        let pid_str = parent_pid.to_string();

        // Send SIGINT (Ctrl+C equivalent)
        if let Ok((_rx, _child)) = self
            .app
            .shell()
            .command("pkill")
            .args(["-INT", "-P", &pid_str])
            .spawn()
        {
            log::info!(
                "Issued SIGINT (Ctrl+C) pkill for descendants of {}",
                parent_pid
            );
        }

        // Wait up to 3 seconds for graceful termination
        std::thread::sleep(Duration::from_secs(3));

        // Escalate to SIGKILL if processes are still running
        if let Ok((_rx, _child)) = self
            .app
            .shell()
            .command("pkill")
            .args(["-KILL", "-P", &pid_str])
            .spawn()
        {
            log::info!(
                "Issued SIGKILL (forceful) pkill for descendants of {}",
                parent_pid
            );
        }
    }

    fn spawn_backend_process(&self) -> Result<(Receiver<CommandEvent>, CommandChild)> {
        log::info!("Command: uv run -m {}", MAIN_MODULE);

        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args(["run", "-m", MAIN_MODULE])
            .current_dir(&self.backend_path);

        sidecar_command
            .spawn()
            .context("Failed to spawn backend process")
    }

    pub fn new(app: AppHandle) -> Result<Self> {
        let resource_root = app
            .path()
            .resolve(".", BaseDirectory::Resource)
            .context("Failed to resolve resource root")?;

        let backend_path = resource_root.join("backend");
        if !backend_path.exists() {
            return Err(anyhow!("Backend directory not found at {:?}", backend_path));
        }

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

    pub fn start_all(&self) -> Result<()> {
        self.install_dependencies()?;

        let mut processes = self.processes.lock().unwrap();

        match self.spawn_backend_process() {
            Ok((rx, child)) => {
                self.stream_backend_logs(rx);
                log::info!("Process {} added to process list", child.pid());
                processes.push(child);
            }
            Err(e) => log::error!("Failed to start backend server: {}", e),
        }

        Ok(())
    }

    /// Stop all backend processes
    pub fn stop_all(&self) {
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
    }

    fn stream_backend_logs(&self, rx: Receiver<CommandEvent>) {
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
