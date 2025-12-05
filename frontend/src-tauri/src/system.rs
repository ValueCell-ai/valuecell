use anyhow::{Context, Result};
use serde_json::json;
use std::fs;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};
use uuid::Uuid;

const CLIENT_ID_FILENAME: &str = "client_id.txt";
const ANALYTICS_ENDPOINT: &str = "https://backend.valuecell.ai/api/v1/analytics/event";

/// Get or create a unique client ID.
/// The client ID is persisted in the app data directory.
/// Uses UUID v7 for generating a timestamp-based unique ID.
pub async fn get_or_create_client_id(app: &AppHandle) -> Result<String> {
    let app_data_dir = app
        .path()
        .resolve("", BaseDirectory::AppData)
        .context("Failed to resolve app data directory")?;
    let client_id_path = app_data_dir.join(CLIENT_ID_FILENAME);

    // Try to read existing client ID
    if let Ok(content) = fs::read_to_string(&client_id_path) {
        let client_id = content.trim().to_string();
        if !client_id.is_empty() {
            return Ok(client_id);
        }
    }

    // Generate new unique client ID using UUID v7 (timestamp-based, ensures uniqueness across devices)
    let client_id = Uuid::now_v7().to_string();

    // Ensure parent directory exists
    if let Some(parent) = client_id_path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create directory: {:?}", parent))?;
    }

    // Write client ID to file
    fs::write(&client_id_path, &client_id)
        .with_context(|| format!("Failed to write client ID to: {:?}", client_id_path))?;

    // Send analytics event to server when creating new client_id (fire and forget)
    let client_id_clone = client_id.clone();
    tauri::async_runtime::spawn(async move {
        if let Err(e) = send_analytics_event(&client_id_clone).await {
            log::warn!(
                "Failed to send analytics event to {}: {e:#}",
                ANALYTICS_ENDPOINT
            );
        }
    });

    Ok(client_id)
}

/// Send analytics event to server with client_id and OS information
async fn send_analytics_event(client_id: &str) -> Result<()> {
    let payload = json!({
        "event": "init",
        "client_id": client_id,
        "os": tauri_plugin_os::platform()
    });

    let client = reqwest::Client::new();
    client
        .post(ANALYTICS_ENDPOINT)
        .json(&payload)
        .send()
        .await
        .context("Failed to send HTTP request")?
        .error_for_status()
        .context("Server returned error status")?;

    Ok(())
}

#[tauri::command]
pub async fn get_client_id(app: tauri::AppHandle) -> Result<String, String> {
    get_or_create_client_id(&app)
        .await
        .map_err(|e| e.to_string())
}
