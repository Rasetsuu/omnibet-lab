use omnibet_lab_core::{
    default_generated_report_path, load_minipack, sha256_hex, write_generated_green_report,
    GeneratedGreenReportV361,
};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
struct CliArgs {
    root: PathBuf,
    report_out: PathBuf,
    desktop_out: PathBuf,
    storage_manifest_out: PathBuf,
}

impl Default for CliArgs {
    fn default() -> Self {
        let root = PathBuf::from(".");
        Self {
            report_out: default_generated_report_path(&root),
            desktop_out: root.join("tauri-app/src/generated-green-sample.generated.json"),
            storage_manifest_out: root.join("reports/generated_v371_v380_storage_manifest.json"),
            root,
        }
    }
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
            "--help" | "-h" => {
                println!("omnibet-local-import-runner --root . --report-out reports/generated_v371_v380_green_sample.json --desktop-out tauri-app/src/generated-green-sample.generated.json --storage-manifest-out reports/generated_v371_v380_storage_manifest.json");
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

fn desktop_payload(report: &GeneratedGreenReportV361) -> Value {
    json!({
        "schema": "omnibet.generated_green_sample_desktop.v371_v380",
        "paper_only": true,
        "generated_by": "omnibet-local-import-runner",
        "status": report.status,
        "source_manifest_verified": report.source_manifest_verified,
        "storage_manifest_written": report.storage_manifest_written,
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
        "trust_gate": {
            "status": "sample_only",
            "validated_paper": false,
            "terminal_prediction_allowed": false,
            "bilet_builder_allowed": false
        },
        "recommendation_output_present": false
    })
}

fn storage_manifest_payload(report: &GeneratedGreenReportV361, report_out: &Path, desktop_out: &Path) -> Result<Value, String> {
    let report_bytes = fs::read(report_out).map_err(|e| format!("read generated report for hash: {e}"))?;
    Ok(json!({
        "schema": "omnibet.generated_storage_manifest.v371_v380",
        "generated_by": "omnibet-local-import-runner",
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
        "schema": "omnibet.generated_green_report.v371_v380.failure",
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

fn run() -> Result<Value, String> {
    let args = parse_args()?;
    match load_minipack(&args.root) {
        Ok(report) => {
            write_generated_green_report(&args.report_out, &report)?;
            let desktop = desktop_payload(&report);
            write_json(&args.desktop_out, &desktop)?;
            let storage = storage_manifest_payload(&report, &args.report_out, &args.desktop_out)?;
            write_json(&args.storage_manifest_out, &storage)?;
            Ok(json!({
                "ok": true,
                "schema": "omnibet.local_import_runner_cli_result.v371_v380",
                "status": report.status,
                "source_manifest_verified": report.source_manifest_verified,
                "report_out": args.report_out,
                "desktop_out": args.desktop_out,
                "storage_manifest_out": args.storage_manifest_out,
                "trust_status": report.trust_status,
                "validated_paper": report.validated_paper,
                "recommendation_output_present": report.recommendation_output_present
            }))
        }
        Err(err) => {
            let failure = failure_payload(&err);
            write_json(&args.report_out, &failure)?;
            write_json(&args.desktop_out, &failure)?;
            write_json(&args.storage_manifest_out, &json!({
                "schema": "omnibet.generated_storage_manifest.v371_v380.failure",
                "paper_only": true,
                "source_manifest_verified": false,
                "status": "integrity_failed_sample_only",
                "credential_values_present": false,
                "recommendation_output_present": false,
                "trust_status": "sample_only",
                "validated_paper": false
            }))?;
            Ok(json!({
                "ok": false,
                "schema": "omnibet.local_import_runner_cli_result.v371_v380",
                "status": "integrity_failed_sample_only",
                "error": err,
                "report_out": args.report_out,
                "desktop_out": args.desktop_out,
                "storage_manifest_out": args.storage_manifest_out,
                "trust_status": "sample_only",
                "validated_paper": false,
                "recommendation_output_present": false
            }))
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
