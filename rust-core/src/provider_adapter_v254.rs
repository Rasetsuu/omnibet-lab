use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAdapterContractsV254 {
    pub schema: String,
    pub contract_id: String,
    pub goal: String,
    pub paper_only: bool,
    pub network_calls_allowed_in_ci: bool,
    pub credentials_stored_in_repo: bool,
    pub live_fetch_enabled: bool,
    pub adapters: Vec<ProviderAdapterContractV254>,
    pub adapter_health_report: AdapterHealthReportContractV254,
    pub desktop_surface: AdapterDesktopSurfaceV254,
    pub acceptance: ProviderAdapterAcceptanceV254,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAdapterContractV254 {
    pub adapter_id: String,
    pub provider_id: String,
    pub provider_class: String,
    pub credential_ref: String,
    pub request_contract: AdapterRequestContractV254,
    pub response_contract: AdapterResponseContractV254,
    pub normalization_targets: Vec<String>,
    pub ci_fixture_only: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AdapterRequestContractV254 {
    pub method: String,
    pub requires_credential: bool,
    pub required_parameters: Vec<String>,
    pub point_in_time_parameter: String,
    pub live_network_allowed_in_ci: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AdapterResponseContractV254 {
    pub fixture_path: String,
    pub top_level_shape: String,
    pub required_fields: Vec<String>,
    pub nested_required_fields: Vec<String>,
    pub timestamp_fields: Vec<String>,
    pub decimal_fields: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AdapterHealthReportContractV254 {
    pub schema: String,
    pub must_report: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AdapterDesktopSurfaceV254 {
    pub show_adapter_contracts: bool,
    pub show_fixture_status: bool,
    pub show_missing_fields: bool,
    pub show_normalization_targets: bool,
    pub live_fetch_button_enabled: bool,
    pub credentials_editable_in_repo: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAdapterAcceptanceV254 {
    pub priority_adapter_contracts_added: bool,
    pub offline_provider_fixtures_added: bool,
    pub rust_contract_validator_added: bool,
    pub adapter_health_report_added: bool,
    pub python_smoke_added: bool,
    pub ci_workflow_added: bool,
    pub no_ci_network_calls: bool,
    pub no_credentials_in_repo: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAdapterValidationReportV254 {
    pub schema: String,
    pub contract_id: String,
    pub ok: bool,
    pub adapter_count: usize,
    pub fixture_count: usize,
    pub health_rows: Vec<ProviderAdapterHealthRowV254>,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAdapterHealthRowV254 {
    pub adapter_id: String,
    pub provider_id: String,
    pub fixture_loaded: bool,
    pub contract_ok: bool,
    pub normalization_targets: Vec<String>,
    pub blockers: Vec<String>,
}

pub fn parse_provider_adapter_contracts_v254(text: &str) -> Result<ProviderAdapterContractsV254, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_provider_adapter_contracts_v254_text(
    contract_text: &str,
    odds_fixture_text: &str,
    football_fixture_text: &str,
) -> Result<ProviderAdapterValidationReportV254, String> {
    let contract = parse_provider_adapter_contracts_v254(contract_text)
        .map_err(|err| format!("parse provider adapter contracts: {}", err))?;
    Ok(validate_provider_adapter_contracts_v254(
        &contract,
        odds_fixture_text,
        football_fixture_text,
    ))
}

pub fn validate_provider_adapter_contracts_v254(
    contract: &ProviderAdapterContractsV254,
    odds_fixture_text: &str,
    football_fixture_text: &str,
) -> ProviderAdapterValidationReportV254 {
    let mut blockers = Vec::new();
    if contract.schema != "omnibet.provider_adapter_contracts.v254" {
        blockers.push(format!("unexpected schema: {}", contract.schema));
    }
    if !contract.paper_only || contract.network_calls_allowed_in_ci || contract.credentials_stored_in_repo || contract.live_fetch_enabled {
        blockers.push("contract must be paper-only, offline in CI, without stored credentials, and live-fetch disabled".to_string());
    }
    if contract.adapters.len() != 2 {
        blockers.push(format!("expected exactly two priority adapter contracts, got {}", contract.adapters.len()));
    }
    if contract.adapter_health_report.schema != "omnibet.provider_adapter_health_report.v254" {
        blockers.push("adapter health report schema mismatch".to_string());
    }
    if !contract.desktop_surface.show_adapter_contracts
        || !contract.desktop_surface.show_fixture_status
        || !contract.desktop_surface.show_missing_fields
        || !contract.desktop_surface.show_normalization_targets
        || contract.desktop_surface.live_fetch_button_enabled
        || contract.desktop_surface.credentials_editable_in_repo
    {
        blockers.push("desktop adapter surface must be visible but read-only".to_string());
    }
    if !contract.acceptance.priority_adapter_contracts_added
        || !contract.acceptance.offline_provider_fixtures_added
        || !contract.acceptance.rust_contract_validator_added
        || !contract.acceptance.adapter_health_report_added
        || !contract.acceptance.python_smoke_added
        || !contract.acceptance.ci_workflow_added
        || !contract.acceptance.no_ci_network_calls
        || !contract.acceptance.no_credentials_in_repo
    {
        blockers.push("acceptance flags are incomplete".to_string());
    }

    let odds_fixture = serde_json::from_str::<Value>(odds_fixture_text).ok();
    let football_fixture = serde_json::from_str::<Value>(football_fixture_text).ok();
    let mut health_rows = Vec::new();

    for adapter in &contract.adapters {
        let fixture_value = if adapter.provider_id == "the_odds_api" {
            odds_fixture.as_ref()
        } else if adapter.provider_id == "api_football" {
            football_fixture.as_ref()
        } else {
            None
        };
        let row = validate_adapter_health_row(adapter, fixture_value);
        if !row.contract_ok {
            blockers.push(format!("adapter contract failed: {}", adapter.adapter_id));
        }
        health_rows.push(row);
    }

    ProviderAdapterValidationReportV254 {
        schema: "omnibet.provider_adapter_validation_report.v254".to_string(),
        contract_id: contract.contract_id.clone(),
        ok: blockers.is_empty(),
        adapter_count: contract.adapters.len(),
        fixture_count: health_rows.iter().filter(|row| row.fixture_loaded).count(),
        health_rows,
        blockers,
    }
}

fn validate_adapter_health_row(adapter: &ProviderAdapterContractV254, fixture: Option<&Value>) -> ProviderAdapterHealthRowV254 {
    let mut blockers = Vec::new();
    if adapter.adapter_id.trim().is_empty() || adapter.provider_id.trim().is_empty() {
        blockers.push("adapter/provider id must be non-empty".to_string());
    }
    if adapter.credential_ref.trim().is_empty() || adapter.credential_ref.contains("SECRET=") {
        blockers.push("credential reference must be symbolic and non-secret".to_string());
    }
    if adapter.request_contract.method != "GET" {
        blockers.push(format!("unsupported method: {}", adapter.request_contract.method));
    }
    if adapter.request_contract.required_parameters.is_empty() || adapter.request_contract.point_in_time_parameter.trim().is_empty() {
        blockers.push("request contract must declare parameters and point-in-time parameter".to_string());
    }
    if adapter.request_contract.live_network_allowed_in_ci || !adapter.ci_fixture_only {
        blockers.push("adapter must remain fixture-only in CI".to_string());
    }
    if adapter.normalization_targets.is_empty() {
        blockers.push("normalization targets are required".to_string());
    }

    let mut fixture_loaded = false;
    if let Some(value) = fixture {
        fixture_loaded = true;
        validate_fixture_shape(adapter, value, &mut blockers);
    } else {
        blockers.push("fixture failed to load".to_string());
    }

    ProviderAdapterHealthRowV254 {
        adapter_id: adapter.adapter_id.clone(),
        provider_id: adapter.provider_id.clone(),
        fixture_loaded,
        contract_ok: blockers.is_empty(),
        normalization_targets: adapter.normalization_targets.clone(),
        blockers,
    }
}

fn validate_fixture_shape(adapter: &ProviderAdapterContractV254, value: &Value, blockers: &mut Vec<String>) {
    match adapter.provider_id.as_str() {
        "the_odds_api" => validate_odds_fixture(value, blockers),
        "api_football" => validate_football_fixture(value, blockers),
        other => blockers.push(format!("unsupported provider fixture validation: {}", other)),
    }
}

fn validate_odds_fixture(value: &Value, blockers: &mut Vec<String>) {
    let Some(items) = value.as_array() else {
        blockers.push("odds fixture must be an array".to_string());
        return;
    };
    if items.is_empty() {
        blockers.push("odds fixture must not be empty".to_string());
        return;
    }
    for item in items {
        require_string(item, &["id"], "id", blockers);
        require_string(item, &["sport_key"], "sport_key", blockers);
        require_timestamp(item, &["commence_time"], "commence_time", blockers);
        require_string(item, &["home_team"], "home_team", blockers);
        require_string(item, &["away_team"], "away_team", blockers);
        let Some(bookmakers) = item.get("bookmakers").and_then(Value::as_array) else {
            blockers.push("bookmakers must be an array".to_string());
            continue;
        };
        if bookmakers.is_empty() {
            blockers.push("bookmakers must not be empty".to_string());
        }
        for bookmaker in bookmakers {
            require_string(bookmaker, &["key"], "bookmakers.key", blockers);
            require_timestamp(bookmaker, &["last_update"], "bookmakers.last_update", blockers);
            let Some(markets) = bookmaker.get("markets").and_then(Value::as_array) else {
                blockers.push("bookmakers.markets must be an array".to_string());
                continue;
            };
            for market in markets {
                require_string(market, &["key"], "bookmakers.markets.key", blockers);
                let Some(outcomes) = market.get("outcomes").and_then(Value::as_array) else {
                    blockers.push("bookmakers.markets.outcomes must be an array".to_string());
                    continue;
                };
                for outcome in outcomes {
                    require_string(outcome, &["name"], "bookmakers.markets.outcomes.name", blockers);
                    require_decimal(outcome, &["price"], "bookmakers.markets.outcomes.price", blockers);
                }
            }
        }
    }
}

fn validate_football_fixture(value: &Value, blockers: &mut Vec<String>) {
    let Some(items) = value.get("response").and_then(Value::as_array) else {
        blockers.push("response must be an array".to_string());
        return;
    };
    if items.is_empty() {
        blockers.push("response must not be empty".to_string());
        return;
    }
    for item in items {
        require_number(item, &["fixture", "id"], "response.fixture.id", blockers);
        require_timestamp(item, &["fixture", "date"], "response.fixture.date", blockers);
        require_number(item, &["teams", "home", "id"], "response.teams.home.id", blockers);
        require_number(item, &["teams", "away", "id"], "response.teams.away.id", blockers);
        require_number(item, &["goals", "home"], "response.goals.home", blockers);
        require_number(item, &["goals", "away"], "response.goals.away", blockers);
        let Some(events) = item.get("events").and_then(Value::as_array) else {
            blockers.push("response.events must be an array".to_string());
            continue;
        };
        for event in events {
            require_number(event, &["time", "elapsed"], "response.events.time.elapsed", blockers);
            require_number(event, &["team", "id"], "response.events.team.id", blockers);
            require_string(event, &["type"], "response.events.type", blockers);
            require_number(event, &["player", "id"], "response.events.player.id", blockers);
        }
    }
}

fn get_path<'a>(value: &'a Value, path: &[&str]) -> Option<&'a Value> {
    let mut current = value;
    for part in path {
        current = current.get(*part)?;
    }
    Some(current)
}

fn require_string(value: &Value, path: &[&str], label: &str, blockers: &mut Vec<String>) {
    match get_path(value, path).and_then(Value::as_str) {
        Some(text) if !text.trim().is_empty() => {}
        _ => blockers.push(format!("missing string field: {}", label)),
    }
}

fn require_number(value: &Value, path: &[&str], label: &str, blockers: &mut Vec<String>) {
    if get_path(value, path).and_then(Value::as_f64).is_none() {
        blockers.push(format!("missing number field: {}", label));
    }
}

fn require_decimal(value: &Value, path: &[&str], label: &str, blockers: &mut Vec<String>) {
    match get_path(value, path).and_then(Value::as_f64) {
        Some(price) if price > 1.0 && price < 1000.0 => {}
        _ => blockers.push(format!("invalid decimal field: {}", label)),
    }
}

fn require_timestamp(value: &Value, path: &[&str], label: &str, blockers: &mut Vec<String>) {
    match get_path(value, path).and_then(Value::as_str) {
        Some(text) if text.len() >= 20 && text.contains('T') && text.ends_with('Z') => {}
        _ => blockers.push(format!("invalid timestamp field: {}", label)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_offline_priority_adapter_contracts() {
        let report = validate_provider_adapter_contracts_v254_text(
            include_str!("../../configs/provider_adapter_contracts.v254.json"),
            include_str!("../../data/provider_fixtures/v254/odds_provider_snapshot.sample.json"),
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
        )
        .expect("validate adapter contracts");
        assert!(report.ok, "{:?}", report.blockers);
        assert_eq!(report.adapter_count, 2);
        assert_eq!(report.fixture_count, 2);
        assert!(report.health_rows.iter().all(|row| row.contract_ok));
        assert!(report.health_rows.iter().any(|row| row.provider_id == "the_odds_api"));
        assert!(report.health_rows.iter().any(|row| row.provider_id == "api_football"));
    }

    #[test]
    fn rejects_bad_fixture_and_live_ci_flag() {
        let mut contract = parse_provider_adapter_contracts_v254(
            include_str!("../../configs/provider_adapter_contracts.v254.json"),
        )
        .expect("parse contracts");
        contract.network_calls_allowed_in_ci = true;
        contract.adapters[0].request_contract.live_network_allowed_in_ci = true;
        let report = validate_provider_adapter_contracts_v254(
            &contract,
            "[]",
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
        );
        assert!(!report.ok);
        assert!(report.blockers.iter().any(|blocker| blocker.contains("offline in CI")));
        assert!(report.health_rows.iter().any(|row| !row.contract_ok));
    }
}
