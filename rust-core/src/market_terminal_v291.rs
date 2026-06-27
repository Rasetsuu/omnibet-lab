use serde_json::Value;

pub fn parse_market_terminal_mvp_contract(text: &str) -> Result<Value, serde_json::Error> {
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

pub fn validate_market_terminal_mvp_contract(contract: &Value) -> Result<(), String> {
    if string_at(contract, "schema") != Some("omnibet.market_terminal_mvp_contract.v291_v300") {
        return Err("unexpected market terminal MVP schema".to_string());
    }
    if bool_at(contract, "paper_only") != Some(true) || bool_at(contract, "local_first") != Some(true) {
        return Err("market terminal MVP must remain paper-only and local-first".to_string());
    }
    if bool_at(contract, "live_provider_calls_allowed") != Some(false)
        || bool_at(contract, "credential_values_allowed") != Some(false)
        || bool_at(contract, "real_money_recommendations_allowed") != Some(false)
    {
        return Err("market terminal MVP must forbid live calls, credentials, and real-money recommendations".to_string());
    }

    require_string_array(
        contract,
        "panel_ids",
        &[
            "market-terminal-summary",
            "market-terminal-fixtures",
            "market-terminal-predictions",
            "market-terminal-selected",
            "market-terminal-watchlist",
            "market-terminal-ledger",
            "market-terminal-bilet-builder",
        ],
    )?;
    require_string_array(contract, "button_ids", &["load-market-terminal-mvp"])?;
    require_string_array(
        contract,
        "fixture_row_required_fields",
        &[
            "canonical_fixture_id",
            "label",
            "competition",
            "status",
            "kickoff_time",
            "source_freshness",
            "available_markets",
            "trust_summary",
        ],
    )?;
    require_string_array(
        contract,
        "prediction_row_required_fields",
        &[
            "canonical_fixture_id",
            "market_key",
            "selection_key",
            "bookmaker_odds_decimal",
            "trust_status",
            "blockers",
            "allowed_action",
            "movement_preview",
        ],
    )?;
    require_string_array(
        contract,
        "forbidden_actions",
        &[
            "recommend_real_bet",
            "place_bet",
            "auto_stake",
            "claim_profitability",
            "enable_bilet_builder_real_mode",
        ],
    )?;
    require_string_array(contract, "allowed_actions", &["inspect", "paper_watch_only"])?;
    require_string_array(
        contract,
        "trust_statuses",
        &["sample_only", "paper_watch", "validated_paper", "unsupported"],
    )?;
    if string_at(contract, "minimum_bilet_builder_status") != Some("validated_paper") {
        return Err("bilet builder must require validated_paper trust".to_string());
    }
    if string_at(contract, "default_disabled_reason") != Some("model_not_validated_for_bilet_builder") {
        return Err("unexpected default disabled reason".to_string());
    }
    require_string_array(
        contract,
        "source_freshness_badges",
        &["fresh_sample", "stale_sample", "missing_timestamp", "offline_sample"],
    )?;

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
    fn validates_market_terminal_mvp_contract() {
        let text = include_str!("../../configs/market_terminal_mvp.v291_v300.json");
        let contract = parse_market_terminal_mvp_contract(text)
            .expect("parse v291-v300 market terminal MVP contract");
        validate_market_terminal_mvp_contract(&contract)
            .expect("validate v291-v300 market terminal MVP contract");
    }
}
