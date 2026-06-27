use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineReportRowV331 {
    pub baseline_id: String,
    pub market_family: String,
    pub baseline_type: String,
    pub status: String,
    pub sample_rows: u64,
    pub eligible_rows: u64,
    pub log_loss: Option<f64>,
    pub brier_score: Option<f64>,
    pub calibration_ece: Option<f64>,
    pub paper_clv_avg: Option<f64>,
    pub blocked_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineArtifactManifestV331 {
    pub artifact_id: String,
    pub artifact_type: String,
    pub created_at: String,
    pub source_report: String,
    pub model_family: String,
    pub market_families: Vec<String>,
    pub training_rows: u64,
    pub status: String,
    pub content_sha256: String,
    pub credential_values_stored: bool,
    pub recommendation_output_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BaselineTrustGateV331 {
    pub status: String,
    pub terminal_prediction_allowed: bool,
    pub bilet_builder_allowed: bool,
    pub requires: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineTrainingReportV331 {
    pub schema: String,
    pub report_id: String,
    pub status: String,
    pub walk_forward_status: String,
    pub baseline_rows: Vec<BaselineReportRowV331>,
    pub artifact_manifest: BaselineArtifactManifestV331,
    pub trust_gate: BaselineTrustGateV331,
    pub blocked_reason: Option<String>,
    pub recommendation_output_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NoVigPreviewV331 {
    pub implied_probabilities: Vec<f64>,
    pub overround: f64,
    pub no_vig_probabilities: Vec<f64>,
}

pub fn parse_baseline_reports_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

fn string_array_contains(value: &Value, key: &str, expected: &str) -> bool {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|items| items.iter().any(|item| item.as_str() == Some(expected)))
        .unwrap_or(false)
}

fn require_string_array(value: &Value, key: &str, required: &[&str]) -> Result<(), String> {
    for item in required {
        if !string_array_contains(value, key, item) {
            return Err(format!("{key} missing required item: {item}"));
        }
    }
    Ok(())
}

pub fn validate_baseline_reports_contract(contract: &Value) -> Result<(), String> {
    if contract.get("schema").and_then(Value::as_str)
        != Some("omnibet.baseline_training_reports_contract.v331_v340")
    {
        return Err("unexpected v331-v340 baseline reports schema".to_string());
    }
    for flag in ["paper_only", "local_first", "training_requires_walk_forward_ready", "blocked_report_required_when_gates_fail"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in ["live_provider_calls_allowed", "credential_values_allowed", "real_money_recommendations_allowed"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    let baselines = contract
        .get("baseline_families")
        .and_then(Value::as_array)
        .ok_or_else(|| "baseline_families missing".to_string())?;
    for baseline_id in [
        "no_vig_1x2_v331",
        "no_vig_totals_v332",
        "no_vig_btts_v333",
        "poisson_elo_team_strength_candidate_v334",
    ] {
        if !baselines.iter().any(|row| row.get("baseline_id").and_then(Value::as_str) == Some(baseline_id)) {
            return Err(format!("missing baseline family: {baseline_id}"));
        }
    }
    require_string_array(
        contract,
        "required_report_fields",
        &[
            "schema",
            "report_id",
            "status",
            "walk_forward_status",
            "baseline_rows",
            "artifact_manifest",
            "trust_gate",
            "blocked_reason",
            "recommendation_output_present",
        ],
    )?;
    require_string_array(
        contract,
        "required_baseline_row_fields",
        &["baseline_id", "market_family", "baseline_type", "status", "sample_rows", "eligible_rows", "blocked_reason"],
    )?;
    require_string_array(
        contract,
        "artifact_manifest_required_fields",
        &["artifact_id", "artifact_type", "created_at", "source_report", "model_family", "training_rows", "status", "content_sha256"],
    )?;
    let trust = contract
        .get("trust_gate")
        .and_then(Value::as_object)
        .ok_or_else(|| "trust_gate missing".to_string())?;
    if trust.get("default_status").and_then(Value::as_str) != Some("blocked_sample") {
        return Err("trust default must be blocked_sample".to_string());
    }
    for required in ["blocked_sample", "sample_only", "experimental_paper", "validated_paper"] {
        if !trust
            .get("allowed_statuses")
            .and_then(Value::as_array)
            .map(|rows| rows.iter().any(|row| row.as_str() == Some(required)))
            .unwrap_or(false)
        {
            return Err(format!("missing trust status: {required}"));
        }
    }
    let forbidden = contract
        .get("forbidden_outputs")
        .and_then(Value::as_array)
        .ok_or_else(|| "forbidden_outputs missing".to_string())?;
    for item in ["real_money_recommendation", "stake_size", "profitability_claim", "live_provider_fetch", "random_train_test_split"] {
        if !forbidden.iter().any(|row| row.as_str() == Some(item)) {
            return Err(format!("forbidden output missing: {item}"));
        }
    }
    let acceptance = contract
        .get("acceptance")
        .and_then(Value::as_object)
        .ok_or_else(|| "acceptance missing".to_string())?;
    for (key, value) in acceptance.iter() {
        if value.as_bool() != Some(true) {
            return Err(format!("acceptance gate not enabled: {key}"));
        }
    }
    Ok(())
}

pub fn no_vig_from_decimal_prices(prices: &[f64]) -> Result<NoVigPreviewV331, String> {
    if prices.len() < 2 {
        return Err("at least two prices are required for a no-vig preview".to_string());
    }
    let mut implied = Vec::with_capacity(prices.len());
    for price in prices {
        if !price.is_finite() || *price <= 1.0 {
            return Err(format!("invalid decimal price: {price}"));
        }
        implied.push(1.0 / *price);
    }
    let overround: f64 = implied.iter().sum();
    if overround <= 0.0 {
        return Err("overround must be positive".to_string());
    }
    let no_vig = implied.iter().map(|p| p / overround).collect();
    Ok(NoVigPreviewV331 {
        implied_probabilities: implied,
        overround,
        no_vig_probabilities: no_vig,
    })
}

pub fn build_baseline_training_report(
    walk_forward_status: &str,
    walk_forward_ready: bool,
    created_at: &str,
) -> BaselineTrainingReportV331 {
    let blocked = !walk_forward_ready || walk_forward_status != "ready_for_evaluation";
    let status = if blocked { "blocked" } else { "ready_for_baseline_reports" };
    let blocked_reason = blocked.then(|| "walk_forward_evaluator_gates_failed".to_string());
    let rows = vec![
        baseline_row("no_vig_1x2_v331", "1x2", "market_implied_no_vig", blocked_reason.clone()),
        baseline_row("no_vig_totals_v332", "totals", "market_implied_no_vig", blocked_reason.clone()),
        baseline_row("no_vig_btts_v333", "btts", "market_implied_no_vig", blocked_reason.clone()),
        baseline_row("poisson_elo_team_strength_candidate_v334", "1x2", "simple_team_strength_candidate", blocked_reason.clone()),
    ];
    let artifact = BaselineArtifactManifestV331 {
        artifact_id: "artifact:baseline:v331_v340:blocked_sample".to_string(),
        artifact_type: "baseline_report_manifest".to_string(),
        created_at: created_at.to_string(),
        source_report: ".omnibet-local/reports/local_v321_v330_walk_forward_evaluator.json".to_string(),
        model_family: "baseline_report_bundle".to_string(),
        market_families: vec!["1x2".to_string(), "totals".to_string(), "btts".to_string()],
        training_rows: if blocked { 0 } else { rows.iter().map(|row| row.eligible_rows).sum() },
        status: if blocked { "blocked_sample" } else { "sample_only" }.to_string(),
        content_sha256: report_content_sha(created_at, status, walk_forward_status),
        credential_values_stored: false,
        recommendation_output_present: false,
    };
    let trust_gate = BaselineTrustGateV331 {
        status: if blocked { "blocked_sample" } else { "sample_only" }.to_string(),
        terminal_prediction_allowed: false,
        bilet_builder_allowed: false,
        requires: vec![
            "walk_forward_ready".to_string(),
            "no_vig_comparison".to_string(),
            "calibration_report".to_string(),
            "clv_report".to_string(),
        ],
    };
    BaselineTrainingReportV331 {
        schema: "omnibet.baseline_training_reports_report.v337".to_string(),
        report_id: "baseline-report:v331-v340:blocked-sample".to_string(),
        status: status.to_string(),
        walk_forward_status: walk_forward_status.to_string(),
        baseline_rows: rows,
        artifact_manifest: artifact,
        trust_gate,
        blocked_reason,
        recommendation_output_present: false,
    }
}

fn baseline_row(
    baseline_id: &str,
    market_family: &str,
    baseline_type: &str,
    blocked_reason: Option<String>,
) -> BaselineReportRowV331 {
    let status = if blocked_reason.is_some() { "blocked" } else { "sample_only" };
    BaselineReportRowV331 {
        baseline_id: baseline_id.to_string(),
        market_family: market_family.to_string(),
        baseline_type: baseline_type.to_string(),
        status: status.to_string(),
        sample_rows: 0,
        eligible_rows: 0,
        log_loss: None,
        brier_score: None,
        calibration_ece: None,
        paper_clv_avg: None,
        blocked_reason,
    }
}

fn report_content_sha(created_at: &str, status: &str, walk_forward_status: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(created_at.as_bytes());
    hasher.update(status.as_bytes());
    hasher.update(walk_forward_status.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn write_baseline_training_report(path: &Path, report: &BaselineTrainingReportV331) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create report directory {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(report)
        .map_err(|e| format!("serialize baseline training report: {e}"))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write baseline training report {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_baseline_reports_contract() {
        let text = include_str!("../../configs/baseline_training_reports.v331_v340.json");
        let contract = parse_baseline_reports_contract(text).expect("parse v331-v340 contract");
        validate_baseline_reports_contract(&contract).expect("validate v331-v340 contract");
    }

    #[test]
    fn computes_no_vig_preview() {
        let preview = no_vig_from_decimal_prices(&[2.05, 3.55, 3.8]).expect("no-vig preview");
        let sum: f64 = preview.no_vig_probabilities.iter().sum();
        assert!((sum - 1.0).abs() < 1e-12);
        assert!(preview.overround > 1.0);
    }

    #[test]
    fn blocks_when_walk_forward_not_ready() {
        let report = build_baseline_training_report("blocked", false, "2026-06-27T00:00:00Z");
        assert_eq!(report.status, "blocked");
        assert_eq!(report.trust_gate.status, "blocked_sample");
        assert_eq!(report.artifact_manifest.training_rows, 0);
        assert!(!report.recommendation_output_present);
        assert!(report.baseline_rows.iter().all(|row| row.status == "blocked"));
    }

    #[test]
    fn writes_baseline_training_report() {
        let report = build_baseline_training_report("blocked", false, "2026-06-27T00:00:00Z");
        let path = std::env::temp_dir().join("omnibet_v331_baseline_report.json");
        write_baseline_training_report(&path, &report).expect("write baseline report");
        let text = fs::read_to_string(&path).expect("read baseline report");
        assert!(text.contains("omnibet.baseline_training_reports_report.v337"));
        fs::remove_file(path).expect("clean baseline report");
    }
}
