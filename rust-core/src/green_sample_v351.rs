use serde_json::Value;

pub fn parse_green_evaluator_sample_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn parse_green_evaluator_sample(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

fn bool_at(value: &Value, key: &str) -> Option<bool> {
    value.get(key).and_then(Value::as_bool)
}

fn string_at<'a>(value: &'a Value, key: &str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

fn array_at<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>, String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{key} must be an array"))
}

fn object_at<'a>(value: &'a Value, key: &str) -> Result<&'a serde_json::Map<String, Value>, String> {
    value
        .get(key)
        .and_then(Value::as_object)
        .ok_or_else(|| format!("{key} must be an object"))
}

fn array_contains_string(value: &Value, key: &str, expected: &str) -> bool {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|rows| rows.iter().any(|row| row.as_str() == Some(expected)))
        .unwrap_or(false)
}

fn require_array_items(value: &Value, key: &str, required: &[&str]) -> Result<(), String> {
    for item in required {
        if !array_contains_string(value, key, item) {
            return Err(format!("{key} missing required item: {item}"));
        }
    }
    Ok(())
}

pub fn validate_green_evaluator_sample_contract(contract: &Value) -> Result<(), String> {
    if string_at(contract, "schema") != Some("omnibet.green_evaluator_sample_contract.v351_v360") {
        return Err("unexpected v351-v360 green evaluator sample contract schema".to_string());
    }
    for flag in ["paper_only", "local_first", "sample_only_allowed"] {
        if bool_at(contract, flag) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in [
        "live_provider_calls_allowed",
        "credential_values_allowed",
        "real_money_recommendations_allowed",
        "validated_paper_allowed",
    ] {
        if bool_at(contract, flag) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    require_array_items(
        contract,
        "required_source_manifest_fields",
        &["source_id", "local_path", "content_sha256", "row_count", "codec", "observed_at_policy", "credential_values_present"],
    )?;
    require_array_items(
        contract,
        "required_fixture_fields",
        &["canonical_fixture_id", "competition_id", "season_id", "home_team_id", "away_team_id", "kickoff_at", "final_result", "settled_at"],
    )?;
    require_array_items(
        contract,
        "required_odds_fields",
        &["canonical_fixture_id", "market_family", "selection_key", "captured_at", "price_decimal", "closing_price_decimal", "source_id"],
    )?;
    require_array_items(
        contract,
        "required_prediction_fields",
        &["canonical_fixture_id", "market_family", "selection_key", "prediction_time", "feature_observed_at", "model_probability", "no_vig_probability", "label_created_at", "settled_at", "outcome"],
    )?;
    let green = object_at(contract, "green_gate_requirements")?;
    if green.get("trust_status").and_then(Value::as_str) != Some("sample_only") {
        return Err("green gate trust_status must remain sample_only".to_string());
    }
    for flag in [
        "feature_observed_at_lte_prediction_time",
        "label_created_at_gte_settled_at",
        "settled_at_gt_prediction_time",
    ] {
        if green.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("green gate {flag} must be true"));
        }
    }
    for flag in ["random_split_used", "recommendation_output_present"] {
        if green.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("green gate {flag} must be false"));
        }
    }
    let forbidden = array_at(contract, "forbidden_outputs")?;
    for item in ["real_money_recommendation", "stake_size", "profitability_claim", "validated_paper_claim", "live_provider_fetch", "random_train_test_split"] {
        if !forbidden.iter().any(|row| row.as_str() == Some(item)) {
            return Err(format!("forbidden output missing: {item}"));
        }
    }
    let acceptance = object_at(contract, "acceptance")?;
    for (key, value) in acceptance.iter() {
        if value.as_bool() != Some(true) {
            return Err(format!("acceptance gate not enabled: {key}"));
        }
    }
    Ok(())
}

pub fn validate_green_evaluator_sample(sample: &Value) -> Result<(), String> {
    if string_at(sample, "schema") != Some("omnibet.green_evaluator_sample.v351_v360") {
        return Err("unexpected v351-v360 green evaluator sample schema".to_string());
    }
    for flag in ["paper_only", "local_first"] {
        if bool_at(sample, flag) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in [
        "credential_values_present",
        "live_provider_calls_present",
        "real_money_recommendations_present",
        "random_split_used",
        "validated_paper_claim_present",
    ] {
        if bool_at(sample, flag) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    if string_at(sample, "trust_status") != Some("sample_only") {
        return Err("trust_status must remain sample_only".to_string());
    }
    let manifests = array_at(sample, "source_manifests")?;
    if manifests.len() < 3 {
        return Err("expected at least three source manifests".to_string());
    }
    for manifest in manifests {
        if manifest.get("credential_values_present").and_then(Value::as_bool) != Some(false) {
            return Err("source manifest contains credential values".to_string());
        }
        if manifest.get("content_sha256").and_then(Value::as_str).map(str::len) != Some(64) {
            return Err("source manifest content_sha256 must be 64 hex chars".to_string());
        }
        if manifest.get("row_count").and_then(Value::as_u64).unwrap_or(0) == 0 {
            return Err("source manifest row_count must be positive".to_string());
        }
    }
    let fixtures = array_at(sample, "fixtures")?;
    let predictions = array_at(sample, "prediction_rows")?;
    if fixtures.len() < 2 {
        return Err("green sample needs at least two fixtures".to_string());
    }
    if predictions.len() < 4 {
        return Err("green sample needs at least four prediction rows".to_string());
    }
    let mut market_families = std::collections::BTreeSet::new();
    for row in predictions {
        let family = row.get("market_family").and_then(Value::as_str).ok_or_else(|| "prediction row missing market_family".to_string())?;
        market_families.insert(family.to_string());
        let prediction_time = row.get("prediction_time").and_then(Value::as_str).ok_or_else(|| "prediction row missing prediction_time".to_string())?;
        let feature_observed_at = row.get("feature_observed_at").and_then(Value::as_str).ok_or_else(|| "prediction row missing feature_observed_at".to_string())?;
        let settled_at = row.get("settled_at").and_then(Value::as_str).ok_or_else(|| "prediction row missing settled_at".to_string())?;
        let label_created_at = row.get("label_created_at").and_then(Value::as_str).ok_or_else(|| "prediction row missing label_created_at".to_string())?;
        if feature_observed_at > prediction_time {
            return Err("feature_observed_at must be <= prediction_time".to_string());
        }
        if settled_at <= prediction_time {
            return Err("settled_at must be after prediction_time".to_string());
        }
        if label_created_at < settled_at {
            return Err("label_created_at must be >= settled_at".to_string());
        }
        for prob_key in ["model_probability", "no_vig_probability"] {
            let prob = row.get(prob_key).and_then(Value::as_f64).ok_or_else(|| format!("{prob_key} missing"))?;
            if !(0.0..=1.0).contains(&prob) {
                return Err(format!("{prob_key} must be in [0, 1]"));
            }
        }
    }
    if market_families.len() < 2 {
        return Err("green sample needs at least two market families".to_string());
    }
    let baseline = object_at(sample, "baseline_report")?;
    if baseline.get("status").and_then(Value::as_str) != Some("ready_for_baseline_reports") {
        return Err("baseline report must be ready_for_baseline_reports".to_string());
    }
    let metric_summary = baseline.get("metric_summary").and_then(Value::as_array).ok_or_else(|| "baseline metric_summary missing".to_string())?;
    if metric_summary.is_empty() {
        return Err("baseline metric_summary must not be empty".to_string());
    }
    for row in metric_summary {
        for metric in ["log_loss", "brier_score", "calibration_ece"] {
            if row.get(metric).and_then(Value::as_f64).is_none() {
                return Err(format!("baseline metric {metric} must be non-null"));
            }
        }
        if row.get("status").and_then(Value::as_str) != Some("sample_only") {
            return Err("baseline metric row must stay sample_only".to_string());
        }
    }
    let calibration = object_at(sample, "calibration_report")?;
    if calibration.get("status").and_then(Value::as_str) != Some("sample_only") {
        return Err("calibration report status must stay sample_only".to_string());
    }
    for key in ["calibration_bins", "no_vig_delta_rows", "paper_clv_summary"] {
        let rows = calibration.get(key).and_then(Value::as_array).ok_or_else(|| format!("{key} missing"))?;
        if rows.is_empty() {
            return Err(format!("{key} must not be empty"));
        }
    }
    for row in calibration.get("calibration_bins").and_then(Value::as_array).unwrap() {
        for metric in ["avg_model_probability", "empirical_hit_rate", "calibration_gap"] {
            if row.get(metric).and_then(Value::as_f64).is_none() {
                return Err(format!("calibration bin metric {metric} must be non-null"));
            }
        }
    }
    for row in calibration.get("paper_clv_summary").and_then(Value::as_array).unwrap() {
        for metric in ["average_clv_decimal", "positive_clv_ratio"] {
            if row.get(metric).and_then(Value::as_f64).is_none() {
                return Err(format!("paper CLV metric {metric} must be non-null"));
            }
        }
    }
    let trust = object_at(sample, "trust_gate")?;
    if trust.get("status").and_then(Value::as_str) != Some("sample_only") {
        return Err("trust gate must remain sample_only".to_string());
    }
    if trust.get("validated_paper").and_then(Value::as_bool) != Some(false) {
        return Err("validated_paper must remain false".to_string());
    }
    for flag in ["terminal_prediction_allowed", "bilet_builder_allowed"] {
        if trust.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must remain false"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_green_evaluator_sample_contract() {
        let text = include_str!("../../configs/green_evaluator_sample.v351_v360.json");
        let contract = parse_green_evaluator_sample_contract(text).expect("parse v351-v360 contract");
        validate_green_evaluator_sample_contract(&contract).expect("validate v351-v360 contract");
    }

    #[test]
    fn validates_green_evaluator_sample() {
        let text = include_str!("../../data/modeling/v351_v360/green_evaluator_sample.sample.json");
        let sample = parse_green_evaluator_sample(text).expect("parse v351-v360 sample");
        validate_green_evaluator_sample(&sample).expect("validate v351-v360 sample");
    }
}
