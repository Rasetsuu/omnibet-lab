use serde_json::Value;

pub fn parse_historical_dataset_foundation_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

fn bool_at<'a>(value: &'a Value, key: &str) -> Option<bool> {
    value.get(key).and_then(Value::as_bool)
}

fn array_at<'a>(value: &'a Value, key: &str) -> Option<&'a Vec<Value>> {
    value.get(key).and_then(Value::as_array)
}

fn string_at<'a>(value: &'a Value, key: &str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

fn object_at<'a>(value: &'a Value, key: &str) -> Option<&'a serde_json::Map<String, Value>> {
    value.get(key).and_then(Value::as_object)
}

fn array_contains_string(rows: &[Value], key: &str, expected: &str) -> bool {
    rows.iter().any(|row| string_at(row, key) == Some(expected))
}

pub fn validate_historical_dataset_foundation_contract(contract: &Value) -> Result<(), String> {
    if string_at(contract, "schema") != Some("omnibet.historical_dataset_foundation_contract.v271_v280") {
        return Err("unexpected historical dataset foundation schema".to_string());
    }
    if bool_at(contract, "paper_only") != Some(true) || bool_at(contract, "local_first") != Some(true) {
        return Err("historical dataset foundation must remain paper-only and local-first".to_string());
    }
    if bool_at(contract, "live_provider_calls_allowed") != Some(false) {
        return Err("historical dataset foundation must not allow live provider calls".to_string());
    }
    if bool_at(contract, "credential_values_allowed") != Some(false) {
        return Err("historical dataset foundation must not allow credential values".to_string());
    }

    let source_matrix = array_at(contract, "source_coverage_matrix")
        .ok_or_else(|| "missing source coverage matrix".to_string())?;
    for required_source in ["football_data_co_uk", "api_football", "the_odds_api", "statsbomb_open_data"] {
        if !array_contains_string(source_matrix, "source_id", required_source) {
            return Err(format!("missing required historical source: {required_source}"));
        }
    }

    let targets = object_at(contract, "league_tournament_targets")
        .ok_or_else(|| "missing league/tournament targets".to_string())?;
    let league_targets = targets
        .get("league_targets")
        .and_then(Value::as_array)
        .ok_or_else(|| "missing league targets".to_string())?;
    let tournament_targets = targets
        .get("tournament_targets")
        .and_then(Value::as_array)
        .ok_or_else(|| "missing tournament targets".to_string())?;
    if league_targets.is_empty() || tournament_targets.is_empty() {
        return Err("league and tournament targets must both be present".to_string());
    }
    if !league_targets.iter().any(|target| {
        target
            .get("minimum_seasons")
            .and_then(Value::as_u64)
            .unwrap_or(0)
            >= 5
    }) {
        return Err("at least one league target must require five seasons".to_string());
    }

    let manifest_bundle = object_at(contract, "historical_source_manifest_bundle")
        .ok_or_else(|| "missing historical source manifest bundle".to_string())?;
    if manifest_bundle.get("target_runtime").and_then(Value::as_str) != Some("rust") {
        return Err("historical source manifest bundle must target rust".to_string());
    }
    let required_manifest_fields = manifest_bundle
        .get("required_manifest_fields")
        .and_then(Value::as_array)
        .ok_or_else(|| "missing required manifest fields".to_string())?;
    for required in ["sha256", "row_count", "observed_at_policy", "promotion_target"] {
        if !required_manifest_fields.iter().any(|field| field.as_str() == Some(required)) {
            return Err(format!("historical manifest missing required field: {required}"));
        }
    }

    let settlement = object_at(contract, "settlement_and_closing_odds_targets")
        .ok_or_else(|| "missing settlement and closing odds targets".to_string())?;
    if settlement.get("paper_clv_required").and_then(Value::as_bool) != Some(true) {
        return Err("paper CLV target must be required".to_string());
    }
    if settlement.get("label_after_settlement_only").and_then(Value::as_bool) != Some(true) {
        return Err("labels must only attach after settlement".to_string());
    }

    let readiness = object_at(contract, "coverage_readiness_report")
        .ok_or_else(|| "missing coverage readiness report".to_string())?;
    if readiness
        .get("minimum_settlement_coverage_ratio")
        .and_then(Value::as_f64)
        .unwrap_or(0.0)
        < 0.95
    {
        return Err("settlement coverage threshold must be high".to_string());
    }

    let build_plan = object_at(contract, "first_dataset_build_plan")
        .ok_or_else(|| "missing first dataset build plan".to_string())?;
    if build_plan.get("target_runtime").and_then(Value::as_str) != Some("rust") {
        return Err("first dataset build plan must target rust".to_string());
    }
    let forbidden = build_plan
        .get("forbidden_actions")
        .and_then(Value::as_array)
        .ok_or_else(|| "missing forbidden actions".to_string())?;
    for forbidden_action in ["random_split", "train_on_unsettled_games", "store_credentials"] {
        if !forbidden.iter().any(|item| item.as_str() == Some(forbidden_action)) {
            return Err(format!("dataset build plan must forbid: {forbidden_action}"));
        }
    }
    if build_plan
        .get("ready_for_training_after_phase")
        .and_then(Value::as_bool)
        != Some(false)
    {
        return Err("historical foundation must not claim training readiness yet".to_string());
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
    fn validates_historical_dataset_foundation_contract() {
        let text = include_str!("../../configs/historical_dataset_foundation.v271_v280.json");
        let contract = parse_historical_dataset_foundation_contract(text)
            .expect("parse v271-v280 historical dataset foundation contract");
        validate_historical_dataset_foundation_contract(&contract)
            .expect("validate v271-v280 historical dataset foundation contract");
    }
}
