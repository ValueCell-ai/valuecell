mod backend;

use backend::BackendManager;
use tauri::Manager;

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            log::info!("🚀 Initializing ValueCell application...");
            
            // Create and start backend manager
            match BackendManager::new(app.handle()) {
                Ok(manager) => {
                    log::info!("✓ Backend manager created");
                    
                    // Start all backend processes
                    if let Err(e) = manager.start_all() {
                        log::error!("❌ Failed to start backend: {}", e);
                        log::error!("The application will continue, but backend features may not work.");
                    }
                    
                    // Store manager in app state for cleanup on exit
                    app.manage(manager);
                }
                Err(e) => {
                    log::error!("❌ Failed to create backend manager: {}", e);
                    log::error!("The application will continue, but backend features may not work.");
                }
            }
            
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
        .invoke_handler(tauri::generate_handler![greet])
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
