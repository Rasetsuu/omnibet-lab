use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WalkForwardWindowV321 {
    pub window_id: String,
    pub train_start: String,
    pub train_end: String,
    pub evaluation_start: String,
    pub evaluation_end: String,
    pub prediction_time: String,
    pub market_family: String,
    pub rows: u64,
    pub coverage_status: String,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WalkForwardRowV321 {
    pub row_id: String,
    pub canonical_fixture_id: String,
    pub window_id: String,
    pub market_family: String,
    pub market_key: String,
    pub selection_key: String,
    pub prediction_time: String,
    pub feature_observed_at: String,
    pub label_created_at: String,
    pub settled_at: String,
    pub has_closing_odds: bool,
    pub has_settlement_label: bool,
    pub eligible_for_evaluation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CoverageReadinessV321 {
    pub minimum_eval_rows: u64,
    pub actual_eval_rows: u64,
    pub minimum_settlement_coverage_ratio: f64,
    pub actual_settlement_coverage_ratio: f64,
    pub minimum_closing_odds_coverage_ratio: f64,
    pub actual_closing_odds_coverage_ratio: f64,
    pub minimum_market_family_rows: u64,
    pub actual_min_market_family_rows: u64,
    pub ready_for_training: bool,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SafetyCheckResultV321 {
    pub check: String,
    pub status: String,
    pub failures: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WalkForwardEvaluatorReportV321 {
    pub schema: String,
    pub status: String,
    pub windows: usize,
    pub total_rows: u64,
    pub eligible_rows: u64,
    pub blocked_rows: u64,
    pub random_split_used: bool,
    pub recommendation_output_present: bool,
    pub safety_checks: Vec<SafetyCheckResultV321>,
    pub coverage_readiness: CoverageReadinessV321,
    pub blockers: Vec<String>,
    pub next_action: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WalkForwardSampleV321 {
    pub schema: String,
    pub sample_id: String,
    pub generated_at: String,
    pub paper_only: bool,
    pub local_first: bool,
    pub credential_values_present: bool,
    pub live_provider_calls_present: bool,
    pub real_money_recommendations_present: bool,
    pub random_split_present: bool,
    pub windows: Vec<WalkForwardWindowV321>,
    pub rows: Vec<WalkForwardRowV321>,
    pub coverage_readiness: CoverageReadinessV321,
}

pub fn parse_walk_forward_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn parse_walk_forward_sample(text: &str) -> Result<WalkForwardSampleV321, serde_json::Error> {
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

pub fn validate_walk_forward_contract(contract: &Value) -> Result<(), String> {
    if contract.get("schema").and_then(Value::as_str)
        != Some("omnibet.walk_forward_evaluator_contract.v321_v330")
    {
        return Err("unexpected v321-v330 walk-forward evaluator schema".to_string());
    }
    for flag in ["paper_only", "local_first"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in [
        "live_provider_calls_allowed",
        "credential_values_allowed",
        "real_money_recommendations_allowed",
        "random_split_allowed",
    ] {
        if contract.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    require_string_array(
        contract,
        "required_safety_checks",
        &[
            "prediction_time_within_evaluation_window",
            "feature_observed_at_lte_prediction_time",
            "label_created_at_gte_settled_at",
            "label_created_at_gt_prediction_time",
            "settled_at_gt_prediction_time",
            "market_family_matches_window",
            "no_random_split",
            "coverage_gate_checked",
        ],
    )?;
    require_string_array(contract, "allowed_market_families", &["1x2", "totals", "btts"])?;
    let gates = contract
        .get("coverage_gates")
        .and_then(Value::as_object)
        .ok_or_else(|| "coverage_gates missing".to_string())?;
    if gates.get("minimum_eval_rows").and_then(Value::as_u64).unwrap_or(0) < 100 {
        return Err("minimum_eval_rows must be at least 100".to_string());
    }
    if gates
        .get("minimum_settlement_coverage_ratio")
        .and_then(Value::as_f64)
        .unwrap_or(0.0)
        < 0.95
    {
        return Err("settlement coverage threshold must stay high".to_string());
    }
    let forbidden = contract
        .get("forbidden_outputs")
        .and_then(Value::as_array)
        .ok_or_else(|| "forbidden_outputs missing".to_string())?;
    for item in ["real_money_recommendation", "stake_size", "profitability_claim", "live_provider_fetch", "random_train_test_split"] {
        if !forbidden.iter().any(|v| v.as_str() == Some(item)) {
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

pub fn evaluate_walk_forward_sample(sample: &WalkForwardSampleV321) -> WalkForwardEvaluatorReportV321 {
    let mut blockers = BTreeSet::new();
    if !sample.paper_only || !sample.local_first {
        blockers.insert("sample_not_paper_local_only".to_string());
    }
    if sample.credential_values_present {
        blockers.insert("credential_values_present".to_string());
    }
    if sample.live_provider_calls_present {
        blockers.insert("live_provider_calls_present".to_string());
    }
    if sample.real_money_recommendations_present {
        blockers.insert("recommendation_output_present".to_string());
    }
    if sample.random_split_present {
        blockers.insert("random_split_present".to_string());
    }

    let window_map: BTreeMap<String, &WalkForwardWindowV321> = sample
        .windows
        .iter()
        .map(|window| (window.window_id.clone(), window))
        .collect();

    let mut failures: BTreeMap<String, u64> = BTreeMap::new();
    for check in [
        "prediction_time_within_evaluation_window",
        "feature_observed_at_lte_prediction_time",
        "label_created_at_gte_settled_at",
        "label_created_at_gt_prediction_time",
        "settled_at_gt_prediction_time",
        "market_family_matches_window",
        "no_random_split",
        "coverage_gate_checked",
    ] {
        failures.insert(check.to_string(), 0);
    }

    if sample.random_split_present {
        *failures.get_mut("no_random_split").unwrap() += 1;
    }

    let mut eligible_rows = 0u64;
    for row in &sample.rows {
        let Some(window) = window_map.get(&row.window_id) else {
            *failures.get_mut("prediction_time_within_evaluation_window").unwrap() += 1;
            blockers.insert(format!("missing_window_for_row:{}", row.row_id));
            continue;
        };
        if row.prediction_time < window.evaluation_start || row.prediction_time > window.evaluation_end {
            *failures.get_mut("prediction_time_within_evaluation_window").unwrap() += 1;
        }
        if row.feature_observed_at > row.prediction_time {
            *failures.get_mut("feature_observed_at_lte_prediction_time").unwrap() += 1;
        }
        if row.label_created_at < row.settled_at {
            *failures.get_mut("label_created_at_gte_settled_at").unwrap() += 1;
        }
        if row.label_created_at <= row.prediction_time {
            *failures.get_mut("label_created_at_gt_prediction_time").unwrap() += 1;
        }
        if row.settled_at <= row.prediction_time {
            *failures.get_mut("settled_at_gt_prediction_time").unwrap() += 1;
        }
        if row.market_family != window.market_family {
            *failures.get_mut("market_family_matches_window").unwrap() += 1;
        }
        if row.eligible_for_evaluation {
            eligible_rows += 1;
        }
    }

    let coverage = &sample.coverage_readiness;
    if !coverage.ready_for_training {
        *failures.get_mut("coverage_gate_checked").unwrap() += 1;
        for blocker in &coverage.blockers {
            blockers.insert(blocker.clone());
        }
    }
    for (check, count) in failures.iter() {
        if *count > 0 {
            blockers.insert(check.clone());
        }
    }

    let safety_checks = failures
        .into_iter()
        .map(|(check, failures)| SafetyCheckResultV321 {
            check,
            status: if failures == 0 { "pass" } else { "fail" }.to_string(),
            failures,
        })
        .collect::<Vec<_>>();

    let blocked_rows = sample.rows.len() as u64 - eligible_rows;
    let status = if blockers.is_empty() && coverage.ready_for_training {
        "ready_for_evaluation"
    } else {
        "blocked"
    };

    WalkForwardEvaluatorReportV321 {
        schema: "omnibet.walk_forward_evaluator_report.v327".to_string(),
        status: status.to_string(),
        windows: sample.windows.len(),
        total_rows: sample.rows.len() as u64,
        eligible_rows,
        blocked_rows,
        random_split_used: sample.random_split_present,
        recommendation_output_present: sample.real_money_recommendations_present,
        safety_checks,
        coverage_readiness: coverage.clone(),
        blockers: blockers.into_iter().collect(),
        next_action: if status == "ready_for_evaluation" {
            "run_baseline_evaluation_reports".to_string()
        } else {
            "increase_local_dataset_coverage_before_training".to_string()
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_walk_forward_contract() {
        let text = include_str!("../../configs/walk_forward_evaluator.v321_v330.json");
        let contract = parse_walk_forward_contract(text).expect("parse v321-v330 contract");
        validate_walk_forward_contract(&contract).expect("validate v321-v330 contract");
    }

    #[test]
    fn evaluator_blocks_on_leakage_and_coverage() {
        let sample = parse_walk_forward_sample(include_str!("../../data/evaluation/v321_v330/walk_forward_evaluator.sample.json"))
            .expect("parse v321-v330 sample");
        let report = evaluate_walk_forward_sample(&sample);
        assert_eq!(report.schema, "omnibet.walk_forward_evaluator_report.v327");
        assert_eq!(report.status, "blocked");
        assert_eq!(report.total_rows, 5);
        assert_eq!(report.eligible_rows, 3);
        assert!(!report.random_split_used);
        assert!(!report.recommendation_output_present);
        assert!(report.blockers.contains(&"feature_observed_at_lte_prediction_time".to_string()));
        assert!(report.blockers.contains(&"minimum_eval_rows_not_met".to_string()));
        assert!(report
            .safety_checks
            .iter()
            .any(|check| check.check == "feature_observed_at_lte_prediction_time" && check.failures == 1));
    }
}
