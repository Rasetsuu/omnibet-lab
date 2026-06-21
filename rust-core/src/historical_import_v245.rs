use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportContract {
    pub schema: String,
    pub import_id: String,
    pub created_at: String,
    pub target_layer: String,
    pub paper_only: bool,
    pub network_calls_allowed_in_ci: bool,
    pub import_windows: Vec<HistoricalImportWindow>,
    pub source_requirements: Vec<HistoricalSourceRequirement>,
    pub leakage_guards: HistoricalLeakageGuards,
    pub settlement_policy: HistoricalSettlementPolicy,
    pub acceptance: HistoricalImportAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportWindow {
    pub window_id: String,
    pub competition_id: String,
    pub season: String,
    pub start_date: String,
    pub end_date: String,
    pub snapshot_cutoff_utc: String,
    pub min_fixture_count: u64,
    pub min_odds_snapshots: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalSourceRequirement {
    pub source_id: String,
    pub source_kind: String,
    pub required: bool,
    pub point_in_time_timestamp_required: bool,
    pub provider_identity_mapping_required: bool,
    pub market_mapping_required: bool,
    pub credentials_must_not_be_persisted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalLeakageGuards {
    pub fixture_start_time_required: bool,
    pub odds_snapshot_time_required: bool,
    pub source_snapshot_time_required: bool,
    pub feature_cutoff_must_precede_fixture_start: bool,
    pub labels_must_not_exist_before_settlement: bool,
    pub closing_odds_kept_separate_from_opening_features: bool,
    pub future_team_form_forbidden: bool,
    pub future_lineup_info_forbidden: bool,
    pub mutable_provider_rows_versioned: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalSettlementPolicy {
    pub settlement_lag_hours: u64,
    pub result_source_required: bool,
    pub void_postponed_abandoned_matches: bool,
    pub market_specific_rules_required: bool,
    pub label_generation_after_settlement_only: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportAcceptance {
    pub rust_contract_types_added: bool,
    pub leakage_guard_validation_added: bool,
    pub source_requirements_validated: bool,
    pub import_window_validation_added: bool,
    pub python_smoke_added: bool,
    pub ci_workflow_added: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportValidationReport {
    pub schema: String,
    pub import_id: String,
    pub ok: bool,
    pub import_window_count: usize,
    pub required_source_count: usize,
    pub errors: Vec<String>,
}

pub fn parse_historical_import_contract(text: &str) -> Result<HistoricalImportContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_historical_import_contract(contract: &HistoricalImportContract) -> HistoricalImportValidationReport {
    let mut errors = Vec::new();
    if contract.schema != "omnibet.historical_import_contract.v245" {
        errors.push(format!("unexpected historical import schema: {}", contract.schema));
    }
    if contract.target_layer != "historical_raw_to_bronze_candidate" {
        errors.push(format!("unexpected target layer: {}", contract.target_layer));
    }
    if !contract.paper_only {
        errors.push("historical import must remain paper-only".to_string());
    }
    if contract.network_calls_allowed_in_ci {
        errors.push("CI historical import contract must not allow network calls".to_string());
    }
    if contract.import_windows.is_empty() {
        errors.push("at least one historical import window is required".to_string());
    }
    let mut window_ids = BTreeSet::new();
    for window in &contract.import_windows {
        if !window_ids.insert(window.window_id.clone()) {
            errors.push(format!("duplicate import window id: {}", window.window_id));
        }
        if window.start_date >= window.end_date {
            errors.push(format!("window start must precede end: {}", window.window_id));
        }
        if window.snapshot_cutoff_utc.is_empty() {
            errors.push(format!("window missing snapshot cutoff: {}", window.window_id));
        }
        if window.min_fixture_count == 0 || window.min_odds_snapshots == 0 {
            errors.push(format!("window minimum counts must be non-zero: {}", window.window_id));
        }
    }
    let required_source_count = contract.source_requirements.iter().filter(|row| row.required).count();
    if required_source_count == 0 {
        errors.push("at least one required source is needed".to_string());
    }
    for source in &contract.source_requirements {
        if source.required {
            if !source.point_in_time_timestamp_required {
                errors.push(format!("required source lacks point-in-time timestamp: {}", source.source_id));
            }
            if !source.provider_identity_mapping_required {
                errors.push(format!("required source lacks identity mapping requirement: {}", source.source_id));
            }
            if !source.market_mapping_required && source.source_kind == "odds" {
                errors.push(format!("odds source lacks market mapping requirement: {}", source.source_id));
            }
            if !source.credentials_must_not_be_persisted {
                errors.push(format!("source may persist credentials: {}", source.source_id));
            }
        }
    }
    let guards = &contract.leakage_guards;
    if !guards.fixture_start_time_required
        || !guards.odds_snapshot_time_required
        || !guards.source_snapshot_time_required
        || !guards.feature_cutoff_must_precede_fixture_start
        || !guards.labels_must_not_exist_before_settlement
        || !guards.closing_odds_kept_separate_from_opening_features
        || !guards.future_team_form_forbidden
        || !guards.future_lineup_info_forbidden
        || !guards.mutable_provider_rows_versioned
    {
        errors.push("all leakage guards must be enabled".to_string());
    }
    let settlement = &contract.settlement_policy;
    if settlement.settlement_lag_hours < 24 {
        errors.push("settlement lag must be at least 24 hours".to_string());
    }
    if !settlement.result_source_required
        || !settlement.void_postponed_abandoned_matches
        || !settlement.market_specific_rules_required
        || !settlement.label_generation_after_settlement_only
    {
        errors.push("all settlement safeguards must be enabled".to_string());
    }
    HistoricalImportValidationReport {
        schema: "omnibet.historical_import_validation_report.v245".to_string(),
        import_id: contract.import_id.clone(),
        ok: errors.is_empty(),
        import_window_count: contract.import_windows.len(),
        required_source_count,
        errors,
    }
}

pub fn validate_historical_import_contract_text(text: &str) -> Result<HistoricalImportValidationReport, String> {
    let contract = parse_historical_import_contract(text)
        .map_err(|e| format!("parse historical import contract: {}", e))?;
    Ok(validate_historical_import_contract(&contract))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_historical_import_contract() {
        let report = validate_historical_import_contract_text(
            include_str!("../../configs/historical_import_contract.v245.json"),
        )
        .expect("validate historical import contract");
        assert!(report.ok, "{:?}", report.errors);
        assert_eq!(report.schema, "omnibet.historical_import_validation_report.v245");
        assert_eq!(report.import_window_count, 2);
        assert_eq!(report.required_source_count, 3);
    }

    #[test]
    fn rejects_leaky_contract() {
        let mut contract = parse_historical_import_contract(
            include_str!("../../configs/historical_import_contract.v245.json"),
        )
        .expect("parse contract");
        contract.leakage_guards.future_lineup_info_forbidden = false;
        contract.settlement_policy.settlement_lag_hours = 0;
        let report = validate_historical_import_contract(&contract);
        assert!(!report.ok);
        assert!(report.errors.iter().any(|err| err.contains("leakage guards")));
        assert!(report.errors.iter().any(|err| err.contains("settlement lag")));
    }
}
