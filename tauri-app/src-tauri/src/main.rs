use serde::Serialize;

#[derive(Serialize)]
struct PackSummaryPayload {
    ok: bool,
    format: &'static str,
    pack_name: &'static str,
    total_rows: u64,
    note: &'static str,
}

#[derive(Serialize)]
struct PredictionPayload {
    ok: bool,
    home_team: String,
    away_team: String,
    model_trust: f64,
    decision_mode: &'static str,
    note: &'static str,
}

#[derive(Serialize)]
struct ValuePayload {
    ok: bool,
    fixture: String,
    mode: &'static str,
    paper_only: bool,
    note: &'static str,
}

#[tauri::command]
fn ping() -> String {
    "omnibet-tauri-ok".to_string()
}

#[tauri::command]
fn pack_summary() -> PackSummaryPayload {
    PackSummaryPayload {
        ok: true,
        format: "omnibet.pack.v1",
        pack_name: "football_core_v1 / football_statsbomb_sample_v1",
        total_rows: 0,
        note: "v18 UI wiring stub. Real pack reads stay in rust-core CLI until the desktop bridge is hardened.",
    }
}

#[tauri::command]
fn predict_fixture(home_team: String, away_team: String) -> PredictionPayload {
    PredictionPayload {
        ok: true,
        home_team,
        away_team,
        model_trust: 0.25,
        decision_mode: "PAPER_ONLY",
        note: "v18 UI wiring stub. Production prediction command will call the Rust model runtime next.",
    }
}

#[tauri::command]
fn value_report(home_team: String, away_team: String) -> ValuePayload {
    ValuePayload {
        ok: true,
        fixture: format!("{} vs {}", home_team, away_team),
        mode: "paper_only",
        paper_only: true,
        note: "v18 UI wiring stub. No real-money staking labels are exposed.",
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ping, pack_summary, predict_fixture, value_report])
        .run(tauri::generate_context!())
        .expect("error while running OmniBet Lab Tauri app");
}
