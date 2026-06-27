use serde_json::Value;

pub fn parse_local_dataset_materialization_contract(text: &str) -> Result<Value, serde_json::Error> {
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

pub fn validate_local_dataset_materialization_contract(contract: &Value) -> Result<(), String> {
    if string_at(contract, "schema") != Some("omnibet.local_dataset_materialization_contract.v301_v310") {
        return Err("unexpected local dataset materialization schema".to_string());
    }
    if bool_at(contract, "paper_only") != Some(true) || bool_at(contract, "local_first") != Some(true) {
        return Err("local dataset materialization must remain paper-only and local-first".to_string());
    }
    if bool_at(contract, "live_provider_calls_allowed") != Some(false)
        || bool_at(contract, "credential_values_allowed") != Some(false)
        || bool_at(contract, "real_money_recommendations_allowed") != Some(false)
        || bool_at(contract, "writes_real_bronze_silver_gold") != Some(false)
    {
        return Err("v301-v310 must forbid live calls, credentials, recommendations, and real writes".to_string());
    }

    require_string_array(
        contract,
        "button_ids",
        &[
            "generate-dataset-materialization-preview",
            "load-dataset-materialization-preview",
            "load-dataset-materialization-sample",
        ],
    )?;
    require_string_array(
        contract,
        "panel_ids",
        &[
            "dataset-materialization-summary",
            "dataset-materialization-manifests",
            "dataset-materialization-fixtures",
            "dataset-materialization-odds",
            "dataset-materialization-settlements",
            "dataset-materialization-clv",
            "dataset-materialization-candidates",
            "dataset-materialization-readiness",
        ],
    )?;
    require_string_array(
        contract,
        "manifest_required_fields",
        &["source_id", "provider", "local_path", "sha256", "row_count", "observed_at_policy", "promotion_target"],
    )?;
    require_string_array(
        contract,
        "candidate_preview_required_fields",
        &["candidate_id", "candidate_type", "target_layer", "codec_target", "row_count", "content_sha256", "promotion_state", "blockers"],
    )?;
    require_string_array(
        contract,
        "allowed_candidate_types",
        &["bronze_raw_candidate", "silver_fact_candidate", "gold_feature_candidate", "market_terminal_preview_candidate"],
    )?;
    require_string_array(contract, "allowed_codecs", &["jsonl.zstd", "parquet.zstd", "jsonl.gzip"])?;

    let thresholds = object_at(contract, "coverage_readiness_thresholds")
        .ok_or_else(|| "missing coverage readiness thresholds".to_string())?;
    if thresholds
        .get("minimum_ready_rows")
        .and_then(Value::as_u64)
        .unwrap_or(0)
        < 1000
    {
        return Err("minimum ready rows must stay at least 1000".to_string());
    }
    if thresholds
        .get("minimum_settlement_coverage_ratio")
        .and_then(Value::as_f64)
        .unwrap_or(0.0)
        < 0.95
    {
        return Err("settlement coverage threshold must stay high".to_string());
    }

    let reload = object_at(contract, "market_terminal_reload")
        .ok_or_else(|| "missing market terminal reload contract".to_string())?;
    if reload.get("enabled").and_then(Value::as_bool) != Some(true) {
        return Err("market terminal reload from generated local preview must be enabled".to_string());
    }
    for forbidden in ["recommend_real_bet", "place_bet", "auto_stake", "claim_profitability"] {
        if !reload
            .get("forbidden_actions")
            .and_then(Value::as_array)
            .map(|items| items.iter().any(|item| item.as_str() == Some(forbidden)))
            .unwrap_or(false)
        {
            return Err(format!("reload contract missing forbidden action: {forbidden}"));
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
    fn validates_local_dataset_materialization_contract() {
        let text = include_str!("../../configs/local_dataset_materialization.v301_v310.json");
        let contract = parse_local_dataset_materialization_contract(text)
            .expect("parse v301-v310 local dataset materialization contract");
        validate_local_dataset_materialization_contract(&contract)
            .expect("validate v301-v310 local dataset materialization contract");
    }
}
