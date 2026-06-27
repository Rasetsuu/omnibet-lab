use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CalibrationBinV341 {
    pub market_family: String,
    pub bin_id: String,
    pub probability_min: f64,
    pub probability_max: f64,
    pub predictions: u64,
    pub avg_model_probability: Option<f64>,
    pub empirical_hit_rate: Option<f64>,
    pub calibration_gap: Option<f64>,
    pub status: String,
    pub blocked_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CalibrationMetricSummaryV341 {
    pub market_family: String,
    pub sample_rows: u64,
    pub eligible_rows: u64,
    pub log_loss: Option<f64>,
    pub brier_score: Option<f64>,
    pub calibration_ece: Option<f64>,
    pub status: String,
    pub blocked_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NoVigDeltaRowV341 {
    pub market_family: String,
    pub selection_key: String,
    pub model_probability: Option<f64>,
    pub no_vig_probability: Option<f64>,
    pub delta_vs_no_vig: Option<f64>,
    pub status: String,
    pub blocked_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PaperClvSummaryV341 {
    pub market_family: String,
    pub paper_watch_rows: u64,
    pub closing_odds_rows: u64,
    pub average_clv_decimal: Option<f64>,
    pub positive_clv_ratio: Option<f64>,
    pub status: String,
    pub blocked_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CalibrationTrustGateV341 {
    pub status: String,
    pub terminal_prediction_allowed: bool,
    pub bilet_builder_allowed: bool,
    pub requires: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CalibrationClvReportV341 {
    pub schema: String,
    pub report_id: String,
    pub status: String,
    pub walk_forward_status: String,
    pub baseline_status: String,
    pub calibration_bins: Vec<CalibrationBinV341>,
    pub metric_summary: Vec<CalibrationMetricSummaryV341>,
    pub no_vig_delta_rows: Vec<NoVigDeltaRowV341>,
    pub paper_clv_summary: Vec<PaperClvSummaryV341>,
    pub trust_gate: CalibrationTrustGateV341,
    pub blocked_reason: Option<String>,
    pub recommendation_output_present: bool,
}

pub fn parse_calibration_clv_contract(text: &str) -> Result<Value, serde_json::Error> {
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

pub fn validate_calibration_clv_contract(contract: &Value) -> Result<(), String> {
    if contract.get("schema").and_then(Value::as_str)
        != Some("omnibet.calibration_clv_reports_contract.v341_v350")
    {
        return Err("unexpected v341-v350 calibration/clv contract schema".to_string());
    }
    for flag in [
        "paper_only",
        "local_first",
        "requires_walk_forward_ready",
        "requires_baseline_reports_ready",
        "blocked_report_required_when_gates_fail",
    ] {
        if contract.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in ["live_provider_calls_allowed", "credential_values_allowed", "real_money_recommendations_allowed"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must be false"));
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
            "baseline_status",
            "calibration_bins",
            "metric_summary",
            "no_vig_delta_rows",
            "paper_clv_summary",
            "trust_gate",
            "blocked_reason",
            "recommendation_output_present",
        ],
    )?;
    require_string_array(
        contract,
        "calibration_bin_required_fields",
        &["market_family", "bin_id", "probability_min", "probability_max", "predictions", "calibration_gap"],
    )?;
    require_string_array(
        contract,
        "metric_summary_required_fields",
        &["market_family", "sample_rows", "eligible_rows", "log_loss", "brier_score", "calibration_ece", "status"],
    )?;
    require_string_array(
        contract,
        "no_vig_delta_required_fields",
        &["market_family", "selection_key", "model_probability", "no_vig_probability", "delta_vs_no_vig", "status"],
    )?;
    require_string_array(
        contract,
        "paper_clv_required_fields",
        &["market_family", "paper_watch_rows", "closing_odds_rows", "average_clv_decimal", "positive_clv_ratio", "status"],
    )?;
    let trust = contract
        .get("trust_gate")
        .and_then(Value::as_object)
        .ok_or_else(|| "trust_gate missing".to_string())?;
    if trust.get("default_status").and_then(Value::as_str) != Some("blocked_sample") {
        return Err("trust default must be blocked_sample".to_string());
    }
    for status in ["blocked_sample", "sample_only", "experimental_paper", "validated_paper"] {
        if !trust
            .get("allowed_statuses")
            .and_then(Value::as_array)
            .map(|items| items.iter().any(|item| item.as_str() == Some(status)))
            .unwrap_or(false)
        {
            return Err(format!("missing trust status: {status}"));
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

pub fn calibration_gap(avg_model_probability: f64, empirical_hit_rate: f64) -> Result<f64, String> {
    for (name, value) in [
        ("avg_model_probability", avg_model_probability),
        ("empirical_hit_rate", empirical_hit_rate),
    ] {
        if !value.is_finite() || !(0.0..=1.0).contains(&value) {
            return Err(format!("{name} must be a probability in [0, 1]"));
        }
    }
    Ok(avg_model_probability - empirical_hit_rate)
}

pub fn brier_score(probability: f64, outcome: f64) -> Result<f64, String> {
    if !probability.is_finite() || !(0.0..=1.0).contains(&probability) {
        return Err("probability must be in [0, 1]".to_string());
    }
    if outcome != 0.0 && outcome != 1.0 {
        return Err("outcome must be 0 or 1".to_string());
    }
    Ok((probability - outcome).powi(2))
}

pub fn no_vig_delta(model_probability: f64, no_vig_probability: f64) -> Result<f64, String> {
    for (name, value) in [("model_probability", model_probability), ("no_vig_probability", no_vig_probability)] {
        if !value.is_finite() || !(0.0..=1.0).contains(&value) {
            return Err(format!("{name} must be a probability in [0, 1]"));
        }
    }
    Ok(model_probability - no_vig_probability)
}

pub fn clv_decimal(captured_price_decimal: f64, closing_price_decimal: f64) -> Result<f64, String> {
    if !captured_price_decimal.is_finite() || captured_price_decimal <= 1.0 {
        return Err("captured price must be a valid decimal odd above 1.0".to_string());
    }
    if !closing_price_decimal.is_finite() || closing_price_decimal <= 1.0 {
        return Err("closing price must be a valid decimal odd above 1.0".to_string());
    }
    Ok((captured_price_decimal / closing_price_decimal) - 1.0)
}

pub fn build_blocked_calibration_clv_report(
    walk_forward_status: &str,
    baseline_status: &str,
) -> CalibrationClvReportV341 {
    let blocked_reason = if baseline_status != "ready_for_baseline_reports" {
        Some("baseline_reports_not_ready".to_string())
    } else if walk_forward_status != "ready_for_evaluation" {
        Some("walk_forward_evaluator_not_ready".to_string())
    } else {
        None
    };
    let status = if blocked_reason.is_some() { "blocked" } else { "sample_only" };
    let market_families = ["1x2", "totals", "btts"];
    CalibrationClvReportV341 {
        schema: "omnibet.calibration_clv_reports_report.v341_v350".to_string(),
        report_id: "calibration-clv-report:v341-v350:blocked-sample".to_string(),
        status: status.to_string(),
        walk_forward_status: walk_forward_status.to_string(),
        baseline_status: baseline_status.to_string(),
        calibration_bins: market_families
            .iter()
            .map(|family| CalibrationBinV341 {
                market_family: (*family).to_string(),
                bin_id: "blocked_sample".to_string(),
                probability_min: 0.0,
                probability_max: 1.0,
                predictions: 0,
                avg_model_probability: None,
                empirical_hit_rate: None,
                calibration_gap: None,
                status: status.to_string(),
                blocked_reason: blocked_reason.clone(),
            })
            .collect(),
        metric_summary: market_families
            .iter()
            .map(|family| CalibrationMetricSummaryV341 {
                market_family: (*family).to_string(),
                sample_rows: 0,
                eligible_rows: 0,
                log_loss: None,
                brier_score: None,
                calibration_ece: None,
                status: status.to_string(),
                blocked_reason: blocked_reason.clone(),
            })
            .collect(),
        no_vig_delta_rows: market_families
            .iter()
            .map(|family| NoVigDeltaRowV341 {
                market_family: (*family).to_string(),
                selection_key: "blocked_sample".to_string(),
                model_probability: None,
                no_vig_probability: None,
                delta_vs_no_vig: None,
                status: status.to_string(),
                blocked_reason: blocked_reason.clone(),
            })
            .collect(),
        paper_clv_summary: market_families
            .iter()
            .map(|family| PaperClvSummaryV341 {
                market_family: (*family).to_string(),
                paper_watch_rows: 0,
                closing_odds_rows: 0,
                average_clv_decimal: None,
                positive_clv_ratio: None,
                status: status.to_string(),
                blocked_reason: blocked_reason.clone(),
            })
            .collect(),
        trust_gate: CalibrationTrustGateV341 {
            status: if blocked_reason.is_some() { "blocked_sample" } else { "sample_only" }.to_string(),
            terminal_prediction_allowed: false,
            bilet_builder_allowed: false,
            requires: vec![
                "walk_forward_ready".to_string(),
                "baseline_reports_ready".to_string(),
                "calibration_report".to_string(),
                "no_vig_delta_report".to_string(),
                "paper_clv_report".to_string(),
            ],
        },
        blocked_reason,
        recommendation_output_present: false,
    }
}

pub fn write_calibration_clv_report(path: &Path, report: &CalibrationClvReportV341) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create report directory {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(report)
        .map_err(|e| format!("serialize calibration/clv report: {e}"))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write calibration/clv report {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_calibration_clv_contract() {
        let text = include_str!("../../configs/calibration_clv_reports.v341_v350.json");
        let contract = parse_calibration_clv_contract(text).expect("parse v341-v350 contract");
        validate_calibration_clv_contract(&contract).expect("validate v341-v350 contract");
    }

    #[test]
    fn computes_report_metrics_helpers() {
        assert!((calibration_gap(0.55, 0.50).unwrap() - 0.05).abs() < 1e-12);
        assert!((brier_score(0.75, 1.0).unwrap() - 0.0625).abs() < 1e-12);
        assert!((no_vig_delta(0.52, 0.48).unwrap() - 0.04).abs() < 1e-12);
        assert!((clv_decimal(2.10, 2.00).unwrap() - 0.05).abs() < 1e-12);
    }

    #[test]
    fn blocks_when_baseline_not_ready() {
        let report = build_blocked_calibration_clv_report("blocked", "blocked");
        assert_eq!(report.status, "blocked");
        assert_eq!(report.trust_gate.status, "blocked_sample");
        assert_eq!(report.blocked_reason, Some("baseline_reports_not_ready".to_string()));
        assert!(!report.recommendation_output_present);
        assert!(report.metric_summary.iter().all(|row| row.log_loss.is_none() && row.brier_score.is_none()));
    }

    #[test]
    fn writes_calibration_clv_report() {
        let report = build_blocked_calibration_clv_report("blocked", "blocked");
        let path = std::env::temp_dir().join("omnibet_v341_calibration_clv_report.json");
        write_calibration_clv_report(&path, &report).expect("write calibration/clv report");
        let text = fs::read_to_string(&path).expect("read calibration/clv report");
        assert!(text.contains("omnibet.calibration_clv_reports_report.v341_v350"));
        fs::remove_file(path).expect("clean calibration/clv report");
    }
}
