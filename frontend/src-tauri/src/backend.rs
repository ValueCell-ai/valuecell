use anyhow::{anyhow, Context, Result};
use std::fs::{self, create_dir_all, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::async_runtime::Receiver;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// Port file name (must match Python's PORT_FILE_NAME)
const PORT_FILE_NAME: &str = "backend.port";

/// Maximum time to wait for port file (in milliseconds)
const PORT_FILE_TIMEOUT_MS: u64 = 30000;

/// Polling interval for port file (in milliseconds)
const PORT_FILE_POLL_MS: u64 = 100;

/// Backend process manager
pub struct BackendManager {
    processes: Mutex<Vec<CommandChild>>,
    backend_path: PathBuf,
    log_dir: PathBuf,
    app: AppHandle,
    /// The port the backend is listening on (discovered from port file)
    port: Mutex<Option<u16>>,
}

const MAIN_MODULE: &str = "valuecell.server.main";
const EXIT_COMMAND: &[u8] = b"__EXIT__\n";
const GRACEFUL_TIMEOUT_SECS: u64 = 3;

impl BackendManager {
    fn wait_until_terminated(mut rx: Receiver<CommandEvent>) {
        while let Some(event) = rx.blocking_recv() {
            if matches!(event, CommandEvent::Terminated(_)) {
                break;
            }
        }
    }

    fn kill_descendants_best_effort(&self, parent_pid: u32) {
        let pid_str = parent_pid.to_string();

        #[cfg(windows)]
        {
            // On Windows, use taskkill to forcefully terminate the process tree
            // /F = Force
            // /T = Tree (child processes)
            // /PID = Process ID
            log::info!("Issued taskkill for descendants of {}", parent_pid);
            // We use std::process::Command directly to avoid needing to configure permissions for taskkill
            if let Err(e) = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid_str])
                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                .output()
            {
                log::error!("Failed to execute taskkill: {}", e);
            }
        }

        #[cfg(not(windows))]
        {
            // Try to kill all descendants of the given PID (macOS/Linux)
            // This is best-effort and ignores errors on platforms without `pkill`.
            // First, send SIGINT (Ctrl+C equivalent) and wait up to 5 seconds.
            // If processes are still running, escalate to SIGKILL.
            
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

    fn request_graceful_then_kill(&self, mut process: CommandChild) {
        let pid = process.pid();
        log::info!("Requesting graceful shutdown for process {}", pid);

        if let Err(err) = process.write(EXIT_COMMAND) {
            log::warn!(
                "Failed to send shutdown command to process {}: {}",
                pid, err
            );
        } else {
            log::info!("Exit command written to process {}", pid);
        }

        std::thread::sleep(Duration::from_secs(GRACEFUL_TIMEOUT_SECS));

        log::info!("Sending forceful shutdown to process {}", pid);
        self.kill_descendants_best_effort(pid);

        if let Err(err) = process.kill() {
            log::error!("Failed to kill process {}: {}", pid, err);
        } else {
            log::info!("Force kill signal sent to process {}", pid);
        }
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
            port: Mutex::new(None),
        })
    }

    /// Get the system config directory path (must match Python's get_system_env_dir)
    fn get_system_config_dir() -> PathBuf {
        #[cfg(target_os = "macos")]
        {
            dirs::home_dir()
                .map(|h| h.join("Library/Application Support/ValueCell"))
                .unwrap_or_else(|| PathBuf::from("/tmp/ValueCell"))
        }

        #[cfg(target_os = "windows")]
        {
            std::env::var("APPDATA")
                .map(PathBuf::from)
                .map(|p| p.join("ValueCell"))
                .unwrap_or_else(|_| {
                    dirs::home_dir()
                        .map(|h| h.join("AppData/Roaming/ValueCell"))
                        .unwrap_or_else(|| PathBuf::from("C:\\ValueCell"))
                })
        }

        #[cfg(target_os = "linux")]
        {
            dirs::home_dir()
                .map(|h| h.join(".config/valuecell"))
                .unwrap_or_else(|| PathBuf::from("/tmp/valuecell"))
        }
    }

    /// Get the port file path
    fn get_port_file_path() -> PathBuf {
        Self::get_system_config_dir().join(PORT_FILE_NAME)
    }

    /// Read the backend port from the port file
    fn read_port_file() -> Option<u16> {
        let port_file = Self::get_port_file_path();
        fs::read_to_string(&port_file)
            .ok()
            .and_then(|s| s.trim().parse::<u16>().ok())
    }

    /// Wait for the port file to appear and read the port
    fn wait_for_port_file(&self) -> Result<u16> {
        let start = std::time::Instant::now();
        let timeout = Duration::from_millis(PORT_FILE_TIMEOUT_MS);

        log::info!("Waiting for backend port file...");

        while start.elapsed() < timeout {
            if let Some(port) = Self::read_port_file() {
                log::info!("Backend port discovered: {}", port);
                return Ok(port);
            }
            std::thread::sleep(Duration::from_millis(PORT_FILE_POLL_MS));
        }

        Err(anyhow!(
            "Timeout waiting for backend port file after {}ms",
            PORT_FILE_TIMEOUT_MS
        ))
    }

    /// Get the backend port (if discovered)
    pub fn get_port(&self) -> Option<u16> {
        *self.port.lock().unwrap()
    }

    /// Get the backend URL
    pub fn get_backend_url(&self) -> Option<String> {
        self.get_port()
            .map(|port| format!("http://127.0.0.1:{}", port))
    }

    fn decide_index_url() -> bool {
        const IPAPI_URL: &str = "https://ipapi.co/json/";
        const TIMEOUT_SECS: u64 = 3;

        let client = match reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(TIMEOUT_SECS))
            .build()
        {
            Ok(c) => c,
            Err(e) => {
                log::warn!("Failed to create HTTP client: {}, using default index", e);
                return false;
            }
        };

        match client.get(IPAPI_URL).send() {
            Ok(response) => {
                if let Ok(json) = response.json::<serde_json::Value>() {
                    let country_code = json
                        .get("country_code")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_uppercase();
                    if country_code == "CN" {
                        return true;
                    }
                }
                false
            }
            Err(e) => {
                log::warn!("Failed to detect region: {}, using default index", e);
                false
            }
        }
    }

    fn install_dependencies(&self) -> Result<()> {
        let should_specify_index_url = Self::decide_index_url();

        let mut args = vec!["sync", "--frozen"];
        let index_url: String;
        if should_specify_index_url {
            index_url = "https://mirrors.aliyun.com/pypi/simple/".to_string();
            args.push("--index-url");
            args.push(&index_url);
        }

        log::info!("Running: uv {}", args.join(" "));

        let sidecar_command = self
            .app
            .shell()
            .sidecar("uv")
            .context("Failed to create uv sidecar command")?
            .args(&args)
            .current_dir(&self.backend_path);

        let (rx, _child) = sidecar_command.spawn().context("Failed to spawn uv sync")?;
        Self::wait_until_terminated(rx);

        log::info!("✓ Dependencies installed/verified");
        Ok(())
    }

    pub fn start_all(&self) -> Result<()> {
        self.install_dependencies()?;

        // Remove stale port file before starting
        let _ = fs::remove_file(Self::get_port_file_path());

        let mut processes = self.processes.lock().unwrap();

        match self.spawn_backend_process() {
            Ok((rx, child)) => {
                self.stream_backend_logs(rx);
                log::info!("Process {} added to process list", child.pid());
                processes.push(child);
            }
            Err(e) => {
                log::error!("Failed to start backend server: {}", e);
                return Err(e);
            }
        }

        // Release lock before waiting for port file
        drop(processes);

        // Wait for port file and store the discovered port
        match self.wait_for_port_file() {
            Ok(port) => {
                *self.port.lock().unwrap() = Some(port);
                log::info!("Backend started on port {}", port);
            }
            Err(e) => {
                log::error!("Failed to discover backend port: {}", e);
                return Err(e);
            }
        }

        Ok(())
    }

    /// Stop all backend processes
    pub fn stop_all(&self) {
        let mut processes = self.processes.lock().unwrap();
        for process in processes.drain(..) {
            self.request_graceful_then_kill(process);
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
                CommandEvent::Terminated(payload) => {
                    log::info!(
                        "Backend process terminated (code: {:?}, signal: {:?})",
                        payload.code,
                        payload.signal
                    );
                    break;
                }
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
