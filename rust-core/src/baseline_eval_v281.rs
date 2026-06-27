use serde_json::Value;

pub fn parse_baseline_training_evaluation_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

fn bool_at(value: &Value, key: &str) -> Option<bool> {
    value.get(key).and_then(Value::as_bool)
}

fn string_at<'a>(value: &'a Value, key: &str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

fn object_at<'a>(value: &'a Value, key: &str) -> Option<&'a serde_json::Map<String, Value>> {
    value.get(key).and_then(Value::as_object)
}

fn array_at<'a>(value: &'a Value, key: &str) -> Option<&'a Vec<Value>> {
    value.get(key).and_then(Value::as_array)
}

fn array_contains_string(rows: &[Value], key: &str, expected: &str) -> bool {
    rows.iter().any(|row| string_at(row, key) == Some(expected))
}

fn string_array_contains(value: &Value, key: &str, expected: &str) -> bool {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|items| items.iter().any(|item| item.as_str() == Some(expected)))
        .unwrap_or(false)
}

pub fn validate_baseline_training_evaluation_contract(contract: &Value) -> Result<(), String> {
    if string_at(contract, "schema") != Some("omnibet.baseline_training_evaluation_contract.v281_v290") {
        return Err("unexpected baseline training evaluation schema".to_string());
    }
    if bool_at(contract, "paper_only") != Some(true) || bool_at(contract, "local_first") != Some(true) {
        return Err("baseline training contract must remain paper-only and local-first".to_string());
    }
    if bool_at(contract, "live_provider_calls_allowed") != Some(false)
        || bool_at(contract, "credential_values_allowed") != Some(false)
        || bool_at(contract, "real_money_recommendations_allowed") != Some(false)
    {
        return Err("baseline training contract must forbid live calls, credentials, and real-money recommendations".to_string());
    }
    if bool_at(contract, "training_on_unsettled_games_allowed") != Some(false)
        || bool_at(contract, "random_split_allowed") != Some(false)
    {
        return Err("baseline training contract must forbid unsettled training and random splits".to_string());
    }

    let dataset = object_at(contract, "dataset_requirements")
        .ok_or_else(|| "missing dataset requirements".to_string())?;
    if dataset.get("storage_contract").and_then(Value::as_str)
        != Some("omnibet.storage_v2_compression_contract.v266_v270")
    {
        return Err("dataset must reference v266-v270 storage contract".to_string());
    }
    if dataset.get("historical_contract").and_then(Value::as_str)
        != Some("omnibet.historical_dataset_foundation_contract.v271_v280")
    {
        return Err("dataset must reference v271-v280 historical contract".to_string());
    }
    for required in ["prediction_time", "feature_observed_at", "label_created_at", "settled_at"] {
        if !string_array_contains(&Value::Object(dataset.clone()), "required_time_columns", required) {
            return Err(format!("dataset missing time column: {required}"));
        }
    }

    let baselines = array_at(contract, "baseline_models")
        .ok_or_else(|| "missing baseline model contracts".to_string())?;
    for market_family in ["1x2", "totals", "btts"] {
        if !array_contains_string(baselines, "market_family", market_family) {
            return Err(format!("missing baseline market family: {market_family}"));
        }
    }
    if !baselines.iter().any(|row| {
        string_at(row, "model_family") == Some("market_baseline")
            && string_at(row, "baseline_id")
                .map(|id| id.contains("no_vig"))
                .unwrap_or(false)
    }) {
        return Err("at least one no-vig market baseline is required".to_string());
    }

    let metrics = object_at(contract, "evaluation_metrics")
        .ok_or_else(|| "missing evaluation metrics".to_string())?;
    for required in ["log_loss", "brier_score", "calibration_ece", "paper_clv_avg", "trust_gate_status"] {
        if !string_array_contains(&Value::Object(metrics.clone()), "required_report_fields", required) {
            return Err(format!("missing required evaluation report field: {required}"));
        }
    }

    let walk_forward = object_at(contract, "walk_forward_evaluation")
        .ok_or_else(|| "missing walk-forward evaluation".to_string())?;
    if walk_forward.get("target_runtime").and_then(Value::as_str) != Some("rust") {
        return Err("walk-forward evaluation must target rust".to_string());
    }
    if walk_forward.get("random_split_allowed").and_then(Value::as_bool) != Some(false) {
        return Err("walk-forward evaluation must forbid random splits".to_string());
    }
    for safety in [
        "feature_observed_at_lte_prediction_time",
        "label_created_after_settlement",
        "no_random_shuffle_split",
        "settlement_coverage_threshold_met",
    ] {
        if !string_array_contains(&Value::Object(walk_forward.clone()), "required_safety_checks", safety) {
            return Err(format!("walk-forward missing safety check: {safety}"));
        }
    }

    let clv = object_at(contract, "paper_clv_report")
        .ok_or_else(|| "missing paper CLV report".to_string())?;
    if clv.get("requires_closing_odds").and_then(Value::as_bool) != Some(true)
        || clv.get("real_stake_allowed").and_then(Value::as_bool) != Some(false)
    {
        return Err("paper CLV must require closing odds and forbid real stake".to_string());
    }

    let trust_gate = object_at(contract, "model_trust_gate")
        .ok_or_else(|| "missing model trust gate".to_string())?;
    if trust_gate.get("default_status").and_then(Value::as_str) != Some("sample_only") {
        return Err("model trust default must be sample_only".to_string());
    }
    if !string_array_contains(&Value::Object(trust_gate.clone()), "allowed_statuses", "validated_paper") {
        return Err("model trust statuses must include validated_paper".to_string());
    }

    let terminal = object_at(contract, "market_terminal_prediction_table")
        .ok_or_else(|| "missing market terminal prediction table".to_string())?;
    for forbidden_action in ["recommend_real_bet", "place_bet", "auto_stake", "claim_profitability"] {
        if !string_array_contains(&Value::Object(terminal.clone()), "forbidden_actions", forbidden_action) {
            return Err(format!("terminal table must forbid: {forbidden_action}"));
        }
    }

    let acceptance = object_at(contract, "acceptance").ok_or_else(|| "missing acceptance".to_string())?;
    for (key, value) in acceptance.iter() {
        if value.as_bool() != Some(true) {
            return Err(format!("acceptance gate not enabled: {key}"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_baseline_training_evaluation_contract() {
        let text = include_str!("../../configs/baseline_training_evaluation.v281_v290.json");
        let contract = parse_baseline_training_evaluation_contract(text)
            .expect("parse v281-v290 baseline training evaluation contract");
        validate_baseline_training_evaluation_contract(&contract)
            .expect("validate v281-v290 baseline training evaluation contract");
    }
}
