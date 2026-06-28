use omnibet_lab_core::{
    build_bronze_fixture_rows_v411, build_bronze_odds_rows_v411, build_bronze_settlement_rows_v411,
    build_gold_candidate_rows_v411, build_historical_materialization_report_v411,
    build_silver_fixture_rows_v411, build_silver_odds_rows_v411, HistoricalFixtureRowV401,
    HistoricalIdentityRowV401, HistoricalOddsRowV401, HistoricalSettlementRowV401,
};
use serde::de::DeserializeOwned;
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
struct CliArgs {
    root: PathBuf,
    report_out: PathBuf,
    manifest_out: PathBuf,
    artifact_dir: PathBuf,
    run_id: String,
}

impl Default for CliArgs {
    fn default() -> Self {
        let root = PathBuf::from(".");
        Self {
            report_out: root.join("reports/generated_historical_materialization_v421_v430_report.json"),
            manifest_out: root.join("reports/materialized/v421_v430/materialization_manifest.json"),
            artifact_dir: root.join("reports/materialized/v421_v430"),
            run_id: default_run_id(),
            root,
        }
    }
}

fn default_run_id() -> String {
    if let Ok(id) = env::var("OMNIBET_MATERIALIZATION_RUN_ID") {
        return sanitize_run_id(&id);
    }
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("materialization_run_{secs}")
}

fn sanitize_run_id(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '_' })
        .collect();
    if cleaned.is_empty() { "materialization_run_unknown".to_string() } else { cleaned }
}

fn parse_args() -> Result<CliArgs, String> {
    let mut args = CliArgs::default();
    let mut iter = env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => args.root = PathBuf::from(iter.next().ok_or("--root requires a value")?),
            "--report-out" => args.report_out = PathBuf::from(iter.next().ok_or("--report-out requires a value")?),
            "--manifest-out" => args.manifest_out = PathBuf::from(iter.next().ok_or("--manifest-out requires a value")?),
            "--artifact-dir" => args.artifact_dir = PathBuf::from(iter.next().ok_or("--artifact-dir requires a value")?),
            "--run-id" => args.run_id = sanitize_run_id(&iter.next().ok_or("--run-id requires a value")?),
            "--help" | "-h" => {
                println!("omnibet-historical-materialization-runner --root . --report-out reports/generated_historical_materialization_v421_v430_report.json --manifest-out reports/materialized/v421_v430/materialization_manifest.json --artifact-dir reports/materialized/v421_v430 --run-id ci_v421_v430");
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }
    Ok(args)
}

fn ensure_parent(path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    Ok(())
}

fn write_json(path: &Path, payload: &Value) -> Result<(), String> {
    ensure_parent(path)?;
    let text = serde_json::to_string_pretty(payload).map_err(|e| format!("serialize {}: {e}", path.display()))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write {}: {e}", path.display()))
}

fn read_rows<T: DeserializeOwned>(path: &Path) -> Result<Vec<T>, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let value = serde_json::from_str::<Value>(&text).map_err(|e| format!("parse {}: {e}", path.display()))?;
    let rows = value
        .get("rows")
        .cloned()
        .ok_or_else(|| format!("{} missing rows", path.display()))?;
    serde_json::from_value::<Vec<T>>(rows).map_err(|e| format!("decode {} rows: {e}", path.display()))
}

fn source_rows(root: &Path) -> Result<(Vec<HistoricalFixtureRowV401>, Vec<HistoricalOddsRowV401>, Vec<HistoricalSettlementRowV401>, Vec<HistoricalIdentityRowV401>), String> {
    let base = root.join("data/historical/v401_v410");
    Ok((
        read_rows::<HistoricalFixtureRowV401>(&base.join("fixtures.sample.json"))?,
        read_rows::<HistoricalOddsRowV401>(&base.join("odds.sample.json"))?,
        read_rows::<HistoricalSettlementRowV401>(&base.join("settlements.sample.json"))?,
        read_rows::<HistoricalIdentityRowV401>(&base.join("identity_map.sample.json"))?,
    ))
}

fn artifact_path(args: &CliArgs, file: &str) -> PathBuf {
    args.artifact_dir.join(file)
}

fn success_payload(args: &CliArgs) -> Result<Value, String> {
    let materialization_report = build_historical_materialization_report_v411(&args.root)?;
    let (fixtures, odds, settlements, identities) = source_rows(&args.root)?;
    let bronze_fixtures = serde_json::to_value(build_bronze_fixture_rows_v411(&fixtures)).map_err(|e| format!("bronze fixtures to value: {e}"))?;
    let bronze_odds = serde_json::to_value(build_bronze_odds_rows_v411(&odds)).map_err(|e| format!("bronze odds to value: {e}"))?;
    let bronze_settlements = serde_json::to_value(build_bronze_settlement_rows_v411(&settlements)).map_err(|e| format!("bronze settlements to value: {e}"))?;
    let silver_fixtures = serde_json::to_value(build_silver_fixture_rows_v411(&fixtures, &identities)).map_err(|e| format!("silver fixtures to value: {e}"))?;
    let silver_odds = serde_json::to_value(build_silver_odds_rows_v411(&odds)).map_err(|e| format!("silver odds to value: {e}"))?;
    let gold_candidates = serde_json::to_value(build_gold_candidate_rows_v411(&odds, &settlements)).map_err(|e| format!("gold candidates to value: {e}"))?;

    fs::create_dir_all(&args.artifact_dir).map_err(|e| format!("create artifact dir {}: {e}", args.artifact_dir.display()))?;
    write_json(&artifact_path(args, "bronze_fixtures.generated.json"), &bronze_fixtures)?;
    write_json(&artifact_path(args, "bronze_odds.generated.json"), &bronze_odds)?;
    write_json(&artifact_path(args, "bronze_settlements.generated.json"), &bronze_settlements)?;
    write_json(&artifact_path(args, "silver_fixtures.generated.json"), &silver_fixtures)?;
    write_json(&artifact_path(args, "silver_odds.generated.json"), &silver_odds)?;
    write_json(&artifact_path(args, "gold_evaluation_candidates.generated.json"), &gold_candidates)?;

    let manifest = serde_json::to_value(&materialization_report.materialization_manifest).map_err(|e| format!("manifest to value: {e}"))?;
    write_json(&args.manifest_out, &manifest)?;

    let report = json!({
        "schema": "omnibet.historical_materialization_command_report.v421_v430",
        "paper_only": true,
        "status": "generated_materialization_preview",
        "run_id": args.run_id,
        "artifact_dir": args.artifact_dir.to_string_lossy(),
        "materialization_report": materialization_report,
        "materialization_manifest": manifest,
        "generated_artifacts": {
            "bronze_fixtures": artifact_path(args, "bronze_fixtures.generated.json").to_string_lossy(),
            "bronze_odds": artifact_path(args, "bronze_odds.generated.json").to_string_lossy(),
            "bronze_settlements": artifact_path(args, "bronze_settlements.generated.json").to_string_lossy(),
            "silver_fixtures": artifact_path(args, "silver_fixtures.generated.json").to_string_lossy(),
            "silver_odds": artifact_path(args, "silver_odds.generated.json").to_string_lossy(),
            "gold_candidates": artifact_path(args, "gold_evaluation_candidates.generated.json").to_string_lossy()
        },
        "ready_for_walk_forward": true,
        "ready_for_training": false,
        "trust_status": "sample_only",
        "credential_values_present": false,
        "recommendation_output_present": false
    });
    write_json(&args.report_out, &report)?;
    write_json(&artifact_path(args, "command_result.json"), &report)?;
    Ok(report)
}

fn failure_payload(args: &CliArgs, error: &str) -> Value {
    json!({
        "schema": "omnibet.historical_materialization_command_report.v421_v430.failure",
        "paper_only": true,
        "status": "materialization_command_failed_sample_only",
        "run_id": args.run_id,
        "error": error,
        "artifact_dir": args.artifact_dir.to_string_lossy(),
        "ready_for_walk_forward": false,
        "ready_for_training": false,
        "trust_status": "sample_only",
        "credential_values_present": false,
        "recommendation_output_present": false
    })
}

fn run() -> Result<Value, String> {
    let args = parse_args()?;
    match success_payload(&args) {
        Ok(payload) => Ok(payload),
        Err(err) => {
            let payload = failure_payload(&args, &err);
            write_json(&args.report_out, &payload)?;
            let _ = fs::create_dir_all(&args.artifact_dir);
            let _ = write_json(&artifact_path(&args, "command_result.json"), &payload);
            Ok(payload)
        }
    }
}

fn main() {
    match run() {
        Ok(payload) => {
            println!("{}", serde_json::to_string_pretty(&payload).unwrap());
            if payload.get("status").and_then(Value::as_str) == Some("materialization_command_failed_sample_only") {
                std::process::exit(1);
            }
        }
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn materialization_run_id_sanitizes_shell_chars() {
        assert_eq!(sanitize_run_id("abc;rm -rf /"), "abc_rm_-rf__");
    }

    #[test]
    fn failure_payload_stays_sample_only() {
        let args = CliArgs::default();
        let payload = failure_payload(&args, "forced failure");
        assert_eq!(payload.get("status").and_then(Value::as_str), Some("materialization_command_failed_sample_only"));
        assert_eq!(payload.get("ready_for_training").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.get("trust_status").and_then(Value::as_str), Some("sample_only"));
        assert_eq!(payload.get("recommendation_output_present").and_then(Value::as_bool), Some(false));
    }
}
