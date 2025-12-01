mod backend;

use backend::BackendManager;
use tauri::{Manager, State};

/// Get the backend URL that the frontend should connect to
#[tauri::command]
fn get_backend_url(manager: State<BackendManager>) -> Option<String> {
    manager.get_backend_url()
}

/// Get the backend port
#[tauri::command]
fn get_backend_port(manager: State<BackendManager>) -> Option<u16> {
    manager.get_port()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            let _ = app
                .get_webview_window("main")
                .expect("no main window")
                .set_focus();
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            let manager = match BackendManager::new(handle) {
                Ok(manager) => manager,
                Err(e) => {
                    log::error!("❌ Failed to create backend manager: {e:#}");
                    return Ok(());
                }
            };

            if let Err(e) = manager.start_all() {
                log::error!("❌ Failed to start backend: {e:#}");
            }

            app.manage(manager);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_url, get_backend_port])
        .on_window_event(|window, event| {
            // Handle window close events to ensure proper cleanup
            if let tauri::WindowEvent::Destroyed = event {
                log::info!("Window destroyed, ensuring backend cleanup...");
                if let Some(manager) = window.app_handle().try_state::<BackendManager>() {
                    manager.stop_all();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // Handle app exit events (e.g., Cmd+Q on Mac)
            if let tauri::RunEvent::Exit = event {
                log::info!("Application exiting, cleaning up backend...");
                if let Some(manager) = app_handle.try_state::<BackendManager>() {
                    manager.stop_all();
                }
            }
        });
}
