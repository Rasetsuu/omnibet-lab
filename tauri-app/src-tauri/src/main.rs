use serde::Serialize;
use serde_json::{json, Value};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize)]
struct CliBridgePayload {
    ok: bool,
    mode: &'static str,
    command: &'static str,
    args: Vec<String>,
    status_code: Option<i32>,
    stdout_json: Option<Value>,
    stdout_text: String,
    stderr_text: String,
    note: String,
}

#[derive(Serialize)]
struct DashboardLoadPayload {
    ok: bool,
    mode: &'static str,
    path: String,
    dashboard_json: Option<Value>,
    error: String,
    note: String,
}

#[derive(Serialize)]
struct ReviewLoadPayload {
    ok: bool,
    mode: &'static str,
    path: String,
    review_json: Option<Value>,
    error: String,
    note: String,
}

#[derive(Serialize)]
struct SettingsLoadPayload {
    ok: bool,
    mode: &'static str,
    path: String,
    settings_json: Option<Value>,
    error: String,
    note: String,
}

#[derive(Serialize)]
struct WorkflowRunPayload {
    ok: bool,
    state: &'static str,
    mode: &'static str,
    workflow_id: String,
    program: String,
    args: Vec<String>,
    status_code: Option<i32>,
    started_at_unix: u64,
    finished_at_unix: u64,
    report_path_hint: String,
    refresh_hint: String,
    stdout_json: Option<Value>,
    stdout_preview: String,
    stderr_preview: String,
    note: String,
}

#[derive(Serialize)]
struct ReviewDecisionSavePayload {
    ok: bool,
    mode: &'static str,
    path: String,
    review_type: String,
    review_id: String,
    decision: String,
    reason: String,
    created_at_unix: u64,
    error: String,
    note: String,
}

fn now_unix() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

fn preview(text: &str) -> String {
    let max_chars = 4000;
    if text.chars().count() <= max_chars {
        return text.to_string();
    }
    text.chars().take(max_chars).collect::<String>() + "\n...truncated..."
}

fn repo_root() -> PathBuf {
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn omnibet_home() -> PathBuf {
    if let Ok(dir) = std::env::var("OMNIBET_HOME") {
        return PathBuf::from(dir);
    }
    repo_root().join(".omnibet-local")
}

fn local_path(rel: &str) -> PathBuf {
    omnibet_home().join(rel)
}

fn ensure_parent(path: &Path) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    Ok(())
}

fn cli_path(bin: &'static str) -> PathBuf {
    if let Ok(dir) = std::env::var("OMNIBET_CLI_DIR") {
        return Path::new(&dir).join(bin);
    }
    repo_root().join("rust-core").join("target").join("debug").join(bin)
}

fn python_program() -> String {
    if let Ok(py) = std::env::var("OMNIBET_PYTHON") {
        return py;
    }
    if cfg!(windows) { "python".to_string() } else { "python3".to_string() }
}

fn run_allowed_cli(bin: &'static str, args: Vec<String>) -> CliBridgePayload {
    let allowed = ["omnibet-pack", "omnibet-infer", "omnibet-value", "omnibet-model"];
    if !allowed.contains(&bin) {
        return CliBridgePayload { ok: false, mode: "blocked", command: bin, args, status_code: None, stdout_json: None, stdout_text: String::new(), stderr_text: "blocked non-allowlisted command".to_string(), note: "Desktop bridge only runs fixed allowlisted Rust CLI binaries; no shell execution.".to_string() };
    }
    let path = cli_path(bin);
    if !path.exists() {
        return CliBridgePayload { ok: false, mode: "cli_missing", command: bin, args, status_code: None, stdout_json: None, stdout_text: String::new(), stderr_text: format!("CLI binary not found: {}", path.display()), note: "Build rust-core first with cargo build, or set OMNIBET_CLI_DIR to the directory containing omnibet-* binaries.".to_string() };
    }
    let output = match Command::new(path).args(&args).output() {
        Ok(out) => out,
        Err(e) => return CliBridgePayload { ok: false, mode: "spawn_error", command: bin, args, status_code: None, stdout_json: None, stdout_text: String::new(), stderr_text: e.to_string(), note: "Failed to start allowlisted Rust CLI command.".to_string() },
    };
    let stdout_text = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr_text = String::from_utf8_lossy(&output.stderr).to_string();
    let stdout_json = serde_json::from_str::<Value>(&stdout_text).ok();
    CliBridgePayload { ok: output.status.success(), mode: "cli", command: bin, args, status_code: output.status.code(), stdout_json, stdout_text, stderr_text, note: "Ran allowlisted Rust CLI without shell. Value outputs remain model-trust gated.".to_string() }
}

fn dashboard_candidate_paths(path_hint: Option<String>) -> Vec<PathBuf> {
    let root = repo_root();
    let mut paths = Vec::new();
    if let Some(hint) = path_hint { if !hint.trim().is_empty() { paths.push(root.join(hint)); } }
    paths.push(local_path("build/v49_dashboard_data.json"));
    paths.push(root.join("build").join("v49_dashboard_data.json"));
    paths.push(root.join("reports").join("ci_v49_dashboard_data.json"));
    paths.push(root.join("tauri-app").join("src").join("dashboard-data.sample.json"));
    paths
}

fn review_candidate_paths(path_hint: Option<String>) -> Vec<PathBuf> {
    let root = repo_root();
    let mut paths = Vec::new();
    if let Some(hint) = path_hint { if !hint.trim().is_empty() { paths.push(root.join(hint)); } }
    paths.push(local_path("build/v53_v54_review_data.json"));
    paths.push(root.join("build").join("v53_v54_review_data.json"));
    paths.push(root.join("reports").join("ci_v53_v54_review_ui.json"));
    paths.push(root.join("tauri-app").join("src").join("review-data.sample.json"));
    paths
}

fn settings_candidate_paths(path_hint: Option<String>) -> Vec<PathBuf> {
    let root = repo_root();
    let mut paths = Vec::new();
    if let Some(hint) = path_hint { if !hint.trim().is_empty() { paths.push(root.join(hint)); } }
    paths.push(local_path("configs/desktop_settings.local.json"));
    paths.push(root.join("configs").join("desktop_settings.local.json"));
    paths.push(root.join("tauri-app").join("src").join("settings-data.sample.json"));
    paths
}

fn load_json_file(path: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str::<Value>(&text).map_err(|e| e.to_string())
}

fn load_first_dashboard_json(path_hint: Option<String>) -> DashboardLoadPayload {
    for path in dashboard_candidate_paths(path_hint) {
        if !path.exists() { continue; }
        match load_json_file(&path) {
            Ok(value) => return DashboardLoadPayload { ok: true, mode: "local_dashboard_json", path: path.display().to_string(), dashboard_json: Some(value), error: String::new(), note: "Loaded local offline dashboard JSON through the Tauri bridge.".to_string() },
            Err(e) => return DashboardLoadPayload { ok: false, mode: "parse_or_read_error", path: path.display().to_string(), dashboard_json: None, error: e, note: "Local dashboard JSON could not be read or parsed.".to_string() },
        }
    }
    DashboardLoadPayload { ok: false, mode: "missing_dashboard_json", path: String::new(), dashboard_json: None, error: "no allowlisted dashboard JSON path exists".to_string(), note: "Generate dashboard data or keep bundled dashboard-data.sample.json available.".to_string() }
}

fn load_first_review_json(path_hint: Option<String>) -> ReviewLoadPayload {
    for path in review_candidate_paths(path_hint) {
        if !path.exists() { continue; }
        match load_json_file(&path) {
            Ok(value) => return ReviewLoadPayload { ok: true, mode: "local_review_json", path: path.display().to_string(), review_json: Some(value), error: String::new(), note: "Loaded local offline review JSON through the Tauri bridge.".to_string() },
            Err(e) => return ReviewLoadPayload { ok: false, mode: "parse_or_read_error", path: path.display().to_string(), review_json: None, error: e, note: "Local review JSON could not be read or parsed.".to_string() },
        }
    }
    ReviewLoadPayload { ok: false, mode: "missing_review_json", path: String::new(), review_json: None, error: "no allowlisted review JSON path exists".to_string(), note: "Generate review data or keep bundled review-data.sample.json available.".to_string() }
}

fn load_first_settings_json(path_hint: Option<String>) -> SettingsLoadPayload {
    for path in settings_candidate_paths(path_hint) {
        if !path.exists() { continue; }
        match load_json_file(&path) {
            Ok(value) => return SettingsLoadPayload { ok: true, mode: "local_settings_json", path: path.display().to_string(), settings_json: Some(value), error: String::new(), note: "Loaded local offline settings JSON; API key values are not displayed.".to_string() },
            Err(e) => return SettingsLoadPayload { ok: false, mode: "parse_or_read_error", path: path.display().to_string(), settings_json: None, error: e, note: "Local settings JSON could not be read or parsed.".to_string() },
        }
    }
    SettingsLoadPayload { ok: false, mode: "missing_settings_json", path: String::new(), settings_json: None, error: "no allowlisted settings JSON path exists".to_string(), note: "Keep bundled settings-data.sample.json available or create configs/desktop_settings.local.json.".to_string() }
}

fn local_workflow_args(workflow_id: &str) -> Option<(Vec<String>, String, String)> {
    match workflow_id {
        "generate_dashboard_report" => Some((vec!["python_lab/dashboard_data_smoke.py".to_string(), "--dashboard-out".to_string(), local_path("build/v49_dashboard_data.json").display().to_string(), "--out".to_string(), local_path("reports/local_v49_dashboard_data.json").display().to_string()], local_path("build/v49_dashboard_data.json").display().to_string(), "dashboard".to_string())),
        "generate_review_report" => Some((vec!["python_lab/review_ui_smoke.py".to_string(), "--review-out".to_string(), local_path("build/v53_v54_review_data.json").display().to_string(), "--out".to_string(), local_path("reports/local_v53_v54_review_ui.json").display().to_string()], local_path("build/v53_v54_review_data.json").display().to_string(), "review".to_string())),
        "run_leak_guard" => Some((vec!["python_lab/leak_guard_smoke.py".to_string(), "--out".to_string(), local_path("reports/local_v40_leak_guard.json").display().to_string()], local_path("reports/local_v40_leak_guard.json").display().to_string(), "features".to_string())),
        "run_feature_export" => Some((vec!["python_lab/feature_export_pack_smoke.py".to_string(), "--out-dir".to_string(), local_path("build/v46_feature_export_pack").display().to_string(), "--out".to_string(), local_path("reports/local_v46_feature_export_pack.json").display().to_string()], local_path("reports/local_v46_feature_export_pack.json").display().to_string(), "features".to_string())),
        "run_settlement_truth" => Some((vec!["python_lab/settlement_truth_smoke.py".to_string(), "--out".to_string(), local_path("reports/local_v38_settlement_truth.json").display().to_string()], local_path("reports/local_v38_settlement_truth.json").display().to_string(), "settlement".to_string())),
        "run_first_model_pass" => Some((vec!["python_lab/first_model_pass_smoke.py".to_string(), "--out".to_string(), local_path("reports/local_v47_first_model_pass.json").display().to_string()], local_path("reports/local_v47_first_model_pass.json").display().to_string(), "models".to_string())),
        _ => None,
    }
}

fn run_allowlisted_workflow(workflow_id: String) -> WorkflowRunPayload {
    let started_at = now_unix();
    let (args, report_path_hint, refresh_hint) = match local_workflow_args(&workflow_id) {
        Some(data) => data,
        None => return WorkflowRunPayload { ok: false, state: "blocked", mode: "blocked", workflow_id, program: String::new(), args: Vec::new(), status_code: None, started_at_unix: started_at, finished_at_unix: now_unix(), report_path_hint: String::new(), refresh_hint: String::new(), stdout_json: None, stdout_preview: String::new(), stderr_preview: "unknown workflow id".to_string(), note: "Only fixed allowlisted offline workflows may run; no shell execution.".to_string() },
    };
    let report_path = PathBuf::from(&report_path_hint);
    let _ = ensure_parent(&report_path);
    let _ = fs::create_dir_all(local_path("logs"));
    let program = python_program();
    let output = match Command::new(&program).current_dir(repo_root()).args(&args).output() {
        Ok(output) => output,
        Err(e) => return WorkflowRunPayload { ok: false, state: "failed", mode: "spawn_error", workflow_id, program, args, status_code: None, started_at_unix: started_at, finished_at_unix: now_unix(), report_path_hint, refresh_hint, stdout_json: None, stdout_preview: String::new(), stderr_preview: e.to_string(), note: "Failed to start allowlisted Python workflow. Set OMNIBET_PYTHON if needed.".to_string() },
    };
    let stdout_text = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr_text = String::from_utf8_lossy(&output.stderr).to_string();
    let stdout_json = serde_json::from_str::<Value>(&stdout_text).ok();
    let ok = output.status.success();
    let payload = WorkflowRunPayload { ok, state: if ok { "completed" } else { "failed" }, mode: "allowlisted_local_workflow", workflow_id: workflow_id.clone(), program, args, status_code: output.status.code(), started_at_unix: started_at, finished_at_unix: now_unix(), report_path_hint: report_path_hint.clone(), refresh_hint: refresh_hint.clone(), stdout_json, stdout_preview: preview(&stdout_text), stderr_preview: preview(&stderr_text), note: "Ran a fixed allowlisted offline workflow without shell execution.".to_string() };
    let log_path = local_path("logs/workflow_runs.jsonl");
    if ensure_parent(&log_path).is_ok() {
        if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&log_path) {
            let _ = writeln!(f, "{}", serde_json::to_string(&payload).unwrap_or_default());
        }
    }
    payload
}

fn normalized_decision(decision: String) -> Option<String> {
    let d = decision.replace("_local", "");
    match d.as_str() { "accepted" | "rejected" | "needs_review" => Some(d), _ => None }
}

fn save_review_decision_impl(review_type: String, review_id: String, decision: String, reason: String) -> ReviewDecisionSavePayload {
    let created_at = now_unix();
    let decision = match normalized_decision(decision) {
        Some(d) => d,
        None => return ReviewDecisionSavePayload { ok: false, mode: "blocked", path: String::new(), review_type, review_id, decision: String::new(), reason, created_at_unix: created_at, error: "unsupported decision".to_string(), note: "Only accepted, rejected, or needs_review decisions may be persisted.".to_string() },
    };
    if review_type != "unknown_market" && review_type != "provider_identity" {
        return ReviewDecisionSavePayload { ok: false, mode: "blocked", path: String::new(), review_type, review_id, decision, reason, created_at_unix: created_at, error: "unsupported review type".to_string(), note: "Only unknown_market and provider_identity review decisions may be persisted.".to_string() };
    }
    let path = local_path("review_decisions/review_decisions.jsonl");
    if let Err(e) = ensure_parent(&path) {
        return ReviewDecisionSavePayload { ok: false, mode: "write_error", path: path.display().to_string(), review_type, review_id, decision, reason, created_at_unix: created_at, error: e.to_string(), note: "Could not create review decision directory.".to_string() };
    }
    let record = json!({ "schema": "omnibet.review_decision.v59", "review_type": review_type, "review_id": review_id, "decision": decision, "reason": reason, "created_at_unix": created_at, "source": "tauri_desktop_local" });
    match OpenOptions::new().create(true).append(true).open(&path).and_then(|mut f| writeln!(f, "{}", record.to_string())) {
        Ok(_) => ReviewDecisionSavePayload { ok: true, mode: "local_review_decision_store", path: path.display().to_string(), review_type: record["review_type"].as_str().unwrap_or_default().to_string(), review_id: record["review_id"].as_str().unwrap_or_default().to_string(), decision: record["decision"].as_str().unwrap_or_default().to_string(), reason: record["reason"].as_str().unwrap_or_default().to_string(), created_at_unix: created_at, error: String::new(), note: "Persisted local review decision. Promotion to production mappings is a later milestone.".to_string() },
        Err(e) => ReviewDecisionSavePayload { ok: false, mode: "write_error", path: path.display().to_string(), review_type: record["review_type"].as_str().unwrap_or_default().to_string(), review_id: record["review_id"].as_str().unwrap_or_default().to_string(), decision: record["decision"].as_str().unwrap_or_default().to_string(), reason: record["reason"].as_str().unwrap_or_default().to_string(), created_at_unix: created_at, error: e.to_string(), note: "Could not append local review decision.".to_string() },
    }
}

#[tauri::command]
fn ping() -> String { "omnibet-tauri-ok".to_string() }

#[tauri::command]
fn load_dashboard_report(path_hint: Option<String>) -> DashboardLoadPayload { load_first_dashboard_json(path_hint) }

#[tauri::command]
fn load_review_report(path_hint: Option<String>) -> ReviewLoadPayload { load_first_review_json(path_hint) }

#[tauri::command]
fn load_app_settings(path_hint: Option<String>) -> SettingsLoadPayload { load_first_settings_json(path_hint) }

#[tauri::command]
fn run_local_workflow(workflow_id: String) -> WorkflowRunPayload { run_allowlisted_workflow(workflow_id) }

#[tauri::command]
fn save_review_decision(review_type: String, review_id: String, decision: String, reason: String) -> ReviewDecisionSavePayload { save_review_decision_impl(review_type, review_id, decision, reason) }

#[tauri::command]
fn pack_summary() -> CliBridgePayload { run_allowed_cli("omnibet-pack", vec!["summary".to_string(), "data_packs/football_core_v1".to_string()]) }

#[tauri::command]
fn predict_fixture(home_team: String, away_team: String) -> CliBridgePayload { run_allowed_cli("omnibet-infer", vec!["predict".to_string(), "data_packs/football_core_v1".to_string(), home_team, away_team]) }

#[tauri::command]
fn value_report(home_team: String, away_team: String) -> CliBridgePayload { run_allowed_cli("omnibet-value", vec!["report".to_string(), "data_packs/football_core_v1".to_string(), home_team, away_team, "data/sample_odds_spain_cape_verde.csv".to_string(), "0.25".to_string()]) }

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping, load_dashboard_report, load_review_report, load_app_settings, run_local_workflow, save_review_decision, pack_summary, predict_fixture, value_report])
        .run(tauri::generate_context!())
        .expect("error while running OmniBet Lab Tauri app");
}
