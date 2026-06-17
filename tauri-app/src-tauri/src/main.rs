#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};

#[tauri::command]
fn ping() -> Value {
    json!({"ok": true, "mode": "tauri_desktop", "paper_only": true})
}

#[tauri::command]
fn pack_summary() -> Value {
    json!({"ok": true, "mode": "local_preview", "summary": "OmniBet Lab desktop beta", "paper_only": true})
}

#[tauri::command]
fn predict_fixture(home: Option<String>, away: Option<String>) -> Value {
    json!({
        "ok": true,
        "mode": "local_prediction_preview",
        "fixture": {"home": home.unwrap_or_default(), "away": away.unwrap_or_default()},
        "prediction": {"home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25},
        "note": "Portable beta preview only; not a recommendation.",
        "paper_only": true
    })
}

#[tauri::command]
fn value_report(home: Option<String>, away: Option<String>) -> Value {
    json!({"ok": true, "mode": "local_report_preview", "fixture": {"home": home.unwrap_or_default(), "away": away.unwrap_or_default()}, "paper_only": true})
}

#[tauri::command]
fn load_dashboard_report(path_hint: Option<String>) -> Value {
    json!({"ok": true, "mode": "packaged_fallback", "path_hint": path_hint, "dashboard_json": null})
}

#[tauri::command]
fn load_review_report(path_hint: Option<String>) -> Value {
    json!({"ok": true, "mode": "packaged_fallback", "path_hint": path_hint, "review_json": null})
}

#[tauri::command]
fn load_app_settings(path_hint: Option<String>) -> Value {
    json!({"ok": true, "mode": "packaged_fallback", "path_hint": path_hint, "settings_json": {"paper_only": true}})
}

#[tauri::command]
fn run_local_workflow(workflow_id: String) -> Value {
    json!({"ok": true, "state": "preview_only", "workflow_id": workflow_id, "paper_only": true})
}

#[tauri::command]
fn save_review_decision(review_type: String, review_id: String, decision: String, reason: String) -> Value {
    json!({"ok": true, "mode": "preview_only", "review_type": review_type, "review_id": review_id, "decision": decision, "reason": reason})
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            ping,
            pack_summary,
            predict_fixture,
            value_report,
            load_dashboard_report,
            load_review_report,
            load_app_settings,
            run_local_workflow,
            save_review_decision
        ])
        .run(tauri::generate_context!())
        .expect("error while running OmniBet Lab desktop beta");
}
