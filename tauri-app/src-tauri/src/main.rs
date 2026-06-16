use serde::Serialize;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::Command;

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

fn repo_root() -> PathBuf {
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn cli_path(bin: &'static str) -> PathBuf {
    if let Ok(dir) = std::env::var("OMNIBET_CLI_DIR") {
        return Path::new(&dir).join(bin);
    }
    repo_root().join("rust-core").join("target").join("debug").join(bin)
}

fn run_allowed_cli(bin: &'static str, args: Vec<String>) -> CliBridgePayload {
    let allowed = ["omnibet-pack", "omnibet-infer", "omnibet-value", "omnibet-model"];
    if !allowed.contains(&bin) {
        return CliBridgePayload {
            ok: false,
            mode: "blocked",
            command: bin,
            args,
            status_code: None,
            stdout_json: None,
            stdout_text: String::new(),
            stderr_text: "blocked non-allowlisted command".to_string(),
            note: "Desktop bridge only runs fixed allowlisted Rust CLI binaries; no shell execution.".to_string(),
        };
    }

    let path = cli_path(bin);
    if !path.exists() {
        return CliBridgePayload {
            ok: false,
            mode: "cli_missing",
            command: bin,
            args,
            status_code: None,
            stdout_json: None,
            stdout_text: String::new(),
            stderr_text: format!("CLI binary not found: {}", path.display()),
            note: "Build rust-core first with cargo build, or set OMNIBET_CLI_DIR to the directory containing omnibet-* binaries.".to_string(),
        };
    }

    let output = match Command::new(path).args(&args).output() {
        Ok(out) => out,
        Err(e) => {
            return CliBridgePayload {
                ok: false,
                mode: "spawn_error",
                command: bin,
                args,
                status_code: None,
                stdout_json: None,
                stdout_text: String::new(),
                stderr_text: e.to_string(),
                note: "Failed to start allowlisted Rust CLI command.".to_string(),
            };
        }
    };

    let stdout_text = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr_text = String::from_utf8_lossy(&output.stderr).to_string();
    let stdout_json = serde_json::from_str::<Value>(&stdout_text).ok();
    CliBridgePayload {
        ok: output.status.success(),
        mode: "cli",
        command: bin,
        args,
        status_code: output.status.code(),
        stdout_json,
        stdout_text,
        stderr_text,
        note: "Ran allowlisted Rust CLI without shell. Value outputs remain model-trust gated.".to_string(),
    }
}

#[tauri::command]
fn ping() -> String {
    "omnibet-tauri-ok".to_string()
}

#[tauri::command]
fn pack_summary() -> CliBridgePayload {
    run_allowed_cli(
        "omnibet-pack",
        vec!["summary".to_string(), "data_packs/football_core_v1".to_string()],
    )
}

#[tauri::command]
fn predict_fixture(home_team: String, away_team: String) -> CliBridgePayload {
    run_allowed_cli(
        "omnibet-infer",
        vec![
            "predict".to_string(),
            "data_packs/football_core_v1".to_string(),
            home_team,
            away_team,
        ],
    )
}

#[tauri::command]
fn value_report(home_team: String, away_team: String) -> CliBridgePayload {
    run_allowed_cli(
        "omnibet-value",
        vec![
            "report".to_string(),
            "data_packs/football_core_v1".to_string(),
            home_team,
            away_team,
            "data/sample_odds_spain_cape_verde.csv".to_string(),
            "0.25".to_string(),
        ],
    )
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping, pack_summary, predict_fixture, value_report])
        .run(tauri::generate_context!())
        .expect("error while running OmniBet Lab Tauri app");
}
