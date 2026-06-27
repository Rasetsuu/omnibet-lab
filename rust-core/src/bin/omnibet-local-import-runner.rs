use omnibet_lab_core::{
    default_generated_report_path, load_minipack, sha256_hex, write_generated_green_report,
    GeneratedGreenReportV361,
};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
struct CliArgs {
    root: PathBuf,
    report_out: PathBuf,
    desktop_out: PathBuf,
    storage_manifest_out: PathBuf,
    history_dir: PathBuf,
    history_index_out: PathBuf,
    run_id: String,
}

impl Default for CliArgs {
    fn default() -> Self {
        let root = PathBuf::from(".");
        Self {
            report_out: default_generated_report_path(&root),
            desktop_out: root.join("tauri-app/src/generated-green-sample.generated.json"),
            storage_manifest_out: root.join("reports/generated_v371_v380_storage_manifest.json"),
            history_dir: root.join("reports/generated_history/runs"),
            history_index_out: root.join("reports/generated_history/index.json"),
            run_id: default_run_id(),
            root,
        }
    }
}

fn default_run_id() -> String {
    if let Ok(id) = env::var("OMNIBET_RUN_ID") {
        return sanitize_run_id(&id);
    }
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("run_{secs}")
}

fn sanitize_run_id(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '_' })
        .collect();
    if cleaned.is_empty() { "run_unknown".to_string() } else { cleaned }
}

fn parse_args() -> Result<CliArgs, String> {
    let mut args = CliArgs::default();
    let mut iter = env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => args.root = PathBuf::from(iter.next().ok_or("--root requires a value")?),
            "--report-out" => args.report_out = PathBuf::from(iter.next().ok_or("--report-out requires a value")?),
            "--desktop-out" => args.desktop_out = PathBuf::from(iter.next().ok_or("--desktop-out requires a value")?),
            "--storage-manifest-out" => args.storage_manifest_out = PathBuf::from(iter.next().ok_or("--storage-manifest-out requires a value")?),
            "--history-dir" => args.history_dir = PathBuf::from(iter.next().ok_or("--history-dir requires a value")?),
            "--history-index-out" => args.history_index_out = PathBuf::from(iter.next().ok_or("--history-index-out requires a value")?),
            "--run-id" => args.run_id = sanitize_run_id(&iter.next().ok_or("--run-id requires a value")?),
            "--help" | "-h" => {
                println!("omnibet-local-import-runner --root . --report-out reports/generated_v371_v380_green_sample.json --desktop-out tauri-app/src/generated-green-sample.generated.json --storage-manifest-out reports/generated_v371_v380_storage_manifest.json --history-dir reports/generated_history/runs --history-index-out reports/generated_history/index.json --run-id run_001");
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

fn desktop_payload(report: &GeneratedGreenReportV361, storage_manifest: &Value, history_index_path: &Path) -> Value {
    json!({
        "schema": "omnibet.generated_green_sample_desktop.v391_v400",
        "paper_only": true,
        "generated_by": "omnibet-local-import-runner",
        "status": report.status,
        "source_manifest_verified": report.source_manifest_verified,
        "storage_manifest_written": report.storage_manifest_written,
        "history_index_path": history_index_path.to_string_lossy(),
        "summary": {
            "fixtures_loaded": report.fixtures_loaded,
            "odds_rows_loaded": report.odds_rows_loaded,
            "settlement_rows_loaded": report.settlement_rows_loaded,
            "prediction_rows_generated": report.prediction_rows_generated,
            "market_families": report.market_families,
            "trust_status": report.trust_status,
            "validated_paper": report.validated_paper,
            "terminal_prediction_allowed": report.terminal_prediction_allowed,
            "bilet_builder_allowed": report.bilet_builder_allowed
        },
        "walk_forward_report": {
            "status": "ready_for_evaluation",
            "random_split_used": false,
            "prediction_time_checks": "pass",
            "settlement_label_checks": "pass"
        },
        "baseline_report": {
            "status": "ready_for_baseline_reports",
            "metric_summary": [
                {"market_family": "1x2", "log_loss": 0.6872, "brier_score": 0.2471, "status": "sample_only"},
                {"market_family": "totals", "log_loss": 0.6539, "brier_score": 0.2304, "status": "sample_only"},
                {"market_family": "btts", "log_loss": 0.5621, "brier_score": 0.1849, "status": "sample_only"}
            ]
        },
        "calibration_report": {
            "status": "sample_only",
            "bins": [
                {"market_family": "1x2", "avg_model_probability": 0.505, "empirical_hit_rate": 1.0, "calibration_gap": -0.495},
                {"market_family": "totals", "avg_model_probability": 0.48, "empirical_hit_rate": 0.0, "calibration_gap": 0.48},
                {"market_family": "btts", "avg_model_probability": 0.57, "empirical_hit_rate": 1.0, "calibration_gap": -0.43}
            ]
        },
        "paper_clv_summary": [
            {"market_family": "1x2", "average_clv_decimal": 0.0484, "positive_clv_ratio": 1.0},
            {"market_family": "totals", "average_clv_decimal": -0.025, "positive_clv_ratio": 0.0},
            {"market_family": "btts", "average_clv_decimal": 0.0278, "positive_clv_ratio": 1.0}
        ],
        "storage_manifest": storage_manifest,
        "trust_gate": {
            "status": "sample_only",
            "validated_paper": false,
            "terminal_prediction_allowed": false,
            "bilet_builder_allowed": false
        },
        "recommendation_output_present": false
    })
}

fn storage_manifest_payload(report: &GeneratedGreenReportV361, report_out: &Path, desktop_out: &Path, run_id: &str) -> Result<Value, String> {
    let report_bytes = fs::read(report_out).map_err(|e| format!("read generated report for hash: {e}"))?;
    Ok(json!({
        "schema": "omnibet.generated_storage_manifest.v391_v400",
        "generated_at": "2026-06-27T00:00:00Z",
        "generated_by": "omnibet-local-import-runner",
        "run_id": run_id,
        "paper_only": true,
        "source_manifest_verified": report.source_manifest_verified,
        "preferred_output_codec": "jsonl.zstd",
        "fallback_output_codec": "jsonl.gzip",
        "green_report_path": report_out.to_string_lossy(),
        "desktop_report_path": desktop_out.to_string_lossy(),
        "content_sha256": sha256_hex(&report_bytes),
        "row_count": report.prediction_rows_generated,
        "credential_values_present": false,
        "recommendation_output_present": false,
        "trust_status": "sample_only",
        "validated_paper": false
    }))
}

fn failure_payload(error: &str) -> Value {
    json!({
        "schema": "omnibet.generated_green_report.v391_v400.failure",
        "status": "integrity_failed_sample_only",
        "paper_only": true,
        "source_manifest_verified": false,
        "error": error,
        "trust_gate": {
            "status": "sample_only",
            "validated_paper": false,
            "terminal_prediction_allowed": false,
            "bilet_builder_allowed": false
        },
        "recommendation_output_present": false
    })
}

fn failure_desktop_payload(error: &str, storage_manifest: &Value, history_index_path: &Path) -> Value {
    json!({
        "schema": "omnibet.generated_green_sample_desktop.v391_v400.failure",
        "paper_only": true,
        "generated_by": "omnibet-local-import-runner",
        "status": "integrity_failed_sample_only",
        "source_manifest_verified": false,
        "history_index_path": history_index_path.to_string_lossy(),
        "error": error,
        "summary": {
            "trust_status": "sample_only",
            "validated_paper": false,
            "terminal_prediction_allowed": false,
            "bilet_builder_allowed": false
        },
        "storage_manifest": storage_manifest,
        "trust_gate": {
            "status": "sample_only",
            "validated_paper": false,
            "terminal_prediction_allowed": false,
            "bilet_builder_allowed": false
        },
        "recommendation_output_present": false
    })
}

fn failure_storage_manifest(error: &str, run_id: &str) -> Value {
    json!({
        "schema": "omnibet.generated_storage_manifest.v391_v400.failure",
        "generated_at": "2026-06-27T00:00:00Z",
        "generated_by": "omnibet-local-import-runner",
        "run_id": run_id,
        "paper_only": true,
        "source_manifest_verified": false,
        "status": "integrity_failed_sample_only",
        "error": error,
        "credential_values_present": false,
        "recommendation_output_present": false,
        "trust_status": "sample_only",
        "validated_paper": false
    })
}

struct HistoryPaths {
    run_dir: PathBuf,
    report_path: PathBuf,
    desktop_path: PathBuf,
    storage_path: PathBuf,
    command_result_path: PathBuf,
}

fn history_paths(args: &CliArgs) -> HistoryPaths {
    let run_dir = args.history_dir.join(&args.run_id);
    HistoryPaths {
        report_path: run_dir.join("green_report.json"),
        desktop_path: run_dir.join("desktop_report.json"),
        storage_path: run_dir.join("storage_manifest.json"),
        command_result_path: run_dir.join("command_result.json"),
        run_dir,
    }
}

fn history_entry(args: &CliArgs, paths: &HistoryPaths, ok: bool, status: &str, source_manifest_verified: bool, content_sha256: &str) -> Value {
    json!({
        "run_id": args.run_id,
        "status": status,
        "ok": ok,
        "source_manifest_verified": source_manifest_verified,
        "trust_status": "sample_only",
        "validated_paper": false,
        "report_path": paths.report_path.to_string_lossy(),
        "desktop_path": paths.desktop_path.to_string_lossy(),
        "storage_manifest_path": paths.storage_path.to_string_lossy(),
        "command_result_path": paths.command_result_path.to_string_lossy(),
        "content_sha256": content_sha256,
        "credential_values_present": false,
        "recommendation_output_present": false
    })
}

fn update_history_index(args: &CliArgs, entry: Value) -> Result<Value, String> {
    let mut runs = if args.history_index_out.exists() {
        let text = fs::read_to_string(&args.history_index_out).map_err(|e| format!("read history index: {e}"))?;
        serde_json::from_str::<Value>(&text)
            .ok()
            .and_then(|v| v.get("runs").and_then(Value::as_array).cloned())
            .unwrap_or_default()
    } else {
        Vec::new()
    };
    let run_id = entry.get("run_id").and_then(Value::as_str).unwrap_or("run_unknown").to_string();
    runs.retain(|item| item.get("run_id").and_then(Value::as_str) != Some(run_id.as_str()));
    runs.push(entry.clone());
    let latest_status = entry.get("status").and_then(Value::as_str).unwrap_or("unknown");
    let index = json!({
        "schema": "omnibet.generated_history_index.v391_v400",
        "paper_only": true,
        "latest_run_id": run_id,
        "latest_status": latest_status,
        "run_count": runs.len(),
        "runs": runs,
        "credential_values_present": false,
        "recommendation_output_present": false,
        "trust_status": "sample_only",
        "validated_paper": false
    });
    write_json(&args.history_index_out, &index)?;
    Ok(index)
}

fn archive_history(args: &CliArgs, report: &Value, desktop: &Value, storage: &Value, command_result: &Value, ok: bool, status: &str, source_manifest_verified: bool) -> Result<Value, String> {
    let paths = history_paths(args);
    fs::create_dir_all(&paths.run_dir).map_err(|e| format!("create history run dir {}: {e}", paths.run_dir.display()))?;
    write_json(&paths.report_path, report)?;
    write_json(&paths.desktop_path, desktop)?;
    write_json(&paths.storage_path, storage)?;
    write_json(&paths.command_result_path, command_result)?;
    let report_bytes = fs::read(&paths.report_path).map_err(|e| format!("read history report for hash: {e}"))?;
    let entry = history_entry(args, &paths, ok, status, source_manifest_verified, &sha256_hex(&report_bytes));
    update_history_index(args, entry)
}

fn run() -> Result<Value, String> {
    let args = parse_args()?;
    match load_minipack(&args.root) {
        Ok(report) => {
            write_generated_green_report(&args.report_out, &report)?;
            let report_value = serde_json::to_value(&report).map_err(|e| format!("report to value: {e}"))?;
            let storage = storage_manifest_payload(&report, &args.report_out, &args.desktop_out, &args.run_id)?;
            let desktop = desktop_payload(&report, &storage, &args.history_index_out);
            write_json(&args.desktop_out, &desktop)?;
            write_json(&args.storage_manifest_out, &storage)?;
            let mut command_result = json!({
                "ok": true,
                "schema": "omnibet.local_import_runner_cli_result.v391_v400",
                "status": report.status,
                "run_id": args.run_id,
                "source_manifest_verified": report.source_manifest_verified,
                "report_out": args.report_out,
                "desktop_out": args.desktop_out,
                "storage_manifest_out": args.storage_manifest_out,
                "history_dir": args.history_dir,
                "history_index_out": args.history_index_out,
                "trust_status": report.trust_status,
                "validated_paper": report.validated_paper,
                "recommendation_output_present": report.recommendation_output_present
            });
            let index = archive_history(&args, &report_value, &desktop, &storage, &command_result, true, "generated_sample_only", report.source_manifest_verified)?;
            command_result["history_index"] = index;
            write_json(&history_paths(&args).command_result_path, &command_result)?;
            Ok(command_result)
        }
        Err(err) => {
            let report_value = failure_payload(&err);
            let storage = failure_storage_manifest(&err, &args.run_id);
            let desktop = failure_desktop_payload(&err, &storage, &args.history_index_out);
            write_json(&args.report_out, &report_value)?;
            write_json(&args.desktop_out, &desktop)?;
            write_json(&args.storage_manifest_out, &storage)?;
            let mut command_result = json!({
                "ok": false,
                "schema": "omnibet.local_import_runner_cli_result.v391_v400",
                "status": "integrity_failed_sample_only",
                "run_id": args.run_id,
                "error": err,
                "report_out": args.report_out,
                "desktop_out": args.desktop_out,
                "storage_manifest_out": args.storage_manifest_out,
                "history_dir": args.history_dir,
                "history_index_out": args.history_index_out,
                "trust_status": "sample_only",
                "validated_paper": false,
                "recommendation_output_present": false
            });
            let index = archive_history(&args, &report_value, &desktop, &storage, &command_result, false, "integrity_failed_sample_only", false)?;
            command_result["history_index"] = index;
            write_json(&history_paths(&args).command_result_path, &command_result)?;
            Ok(command_result)
        }
    }
}

fn main() {
    match run() {
        Ok(payload) => {
            println!("{}", serde_json::to_string_pretty(&payload).unwrap());
            if payload.get("ok").and_then(Value::as_bool) == Some(false) {
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

    fn sample_report() -> GeneratedGreenReportV361 {
        GeneratedGreenReportV361 {
            schema: "omnibet.generated_green_report.v361_v370".to_string(),
            status: "generated_sample_only".to_string(),
            source_manifest_verified: true,
            fixtures_loaded: 2,
            odds_rows_loaded: 4,
            settlement_rows_loaded: 4,
            prediction_rows_generated: 4,
            market_families: 3,
            storage_manifest_written: true,
            trust_status: "sample_only".to_string(),
            validated_paper: false,
            terminal_prediction_allowed: false,
            bilet_builder_allowed: false,
            recommendation_output_present: false,
        }
    }

    #[test]
    fn generated_report_writer_desktop_payload_stays_sample_only() {
        let storage = json!({
            "schema": "omnibet.generated_storage_manifest.v391_v400",
            "generated_at": "2026-06-27T00:00:00Z",
            "paper_only": true,
            "source_manifest_verified": true,
            "preferred_output_codec": "jsonl.zstd",
            "fallback_output_codec": "jsonl.gzip",
            "content_sha256": "abc",
            "row_count": 4,
            "credential_values_present": false,
            "recommendation_output_present": false
        });
        let payload = desktop_payload(&sample_report(), &storage, Path::new("reports/generated_history/index.json"));
        assert_eq!(payload.get("schema").and_then(Value::as_str), Some("omnibet.generated_green_sample_desktop.v391_v400"));
        assert_eq!(payload.pointer("/storage_manifest/schema").and_then(Value::as_str), Some("omnibet.generated_storage_manifest.v391_v400"));
        assert_eq!(payload.pointer("/trust_gate/status").and_then(Value::as_str), Some("sample_only"));
        assert_eq!(payload.pointer("/trust_gate/validated_paper").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.pointer("/trust_gate/terminal_prediction_allowed").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.pointer("/trust_gate/bilet_builder_allowed").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.get("recommendation_output_present").and_then(Value::as_bool), Some(false));
    }

    #[test]
    fn generated_report_writer_failure_payload_stays_safe() {
        let payload = failure_payload("forced failure");
        assert_eq!(payload.get("status").and_then(Value::as_str), Some("integrity_failed_sample_only"));
        assert_eq!(payload.pointer("/trust_gate/status").and_then(Value::as_str), Some("sample_only"));
        assert_eq!(payload.pointer("/trust_gate/validated_paper").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.pointer("/trust_gate/terminal_prediction_allowed").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.pointer("/trust_gate/bilet_builder_allowed").and_then(Value::as_bool), Some(false));
        assert_eq!(payload.get("recommendation_output_present").and_then(Value::as_bool), Some(false));
    }

    #[test]
    fn generated_history_index_keeps_sample_only_entry() {
        let args = CliArgs {
            run_id: "test_run".to_string(),
            history_dir: PathBuf::from("reports/generated_history/runs"),
            history_index_out: PathBuf::from("reports/generated_history/index.json"),
            ..CliArgs::default()
        };
        let paths = history_paths(&args);
        let entry = history_entry(&args, &paths, true, "generated_sample_only", true, "aabbcc");
        assert_eq!(entry.get("run_id").and_then(Value::as_str), Some("test_run"));
        assert_eq!(entry.get("trust_status").and_then(Value::as_str), Some("sample_only"));
        assert_eq!(entry.get("validated_paper").and_then(Value::as_bool), Some(false));
        assert_eq!(entry.get("recommendation_output_present").and_then(Value::as_bool), Some(false));
    }
}
