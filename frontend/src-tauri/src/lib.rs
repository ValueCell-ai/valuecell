mod backend;

use backend::BackendManager;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
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
