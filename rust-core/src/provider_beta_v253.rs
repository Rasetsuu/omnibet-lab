use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderDataBetaMatrix {
    pub schema: String,
    pub matrix_id: String,
    pub goal: String,
    pub paper_only: bool,
    pub network_calls_allowed_in_ci: bool,
    pub credentials_stored_in_repo: bool,
    pub providers: Vec<ProviderBetaSource>,
    pub historical_coverage_targets: Vec<HistoricalCoverageTarget>,
    pub desktop_surface: ProviderDesktopSurface,
    pub acceptance: ProviderDataBetaAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderBetaSource {
    pub provider_id: String,
    pub provider_class: String,
    pub adapter_status: String,
    pub credential_mode: String,
    pub credential_env_var: Option<String>,
    pub supports_fixtures: bool,
    pub supports_odds_snapshots: bool,
    pub supports_results: bool,
    pub supports_lineups_events: bool,
    pub historical_depth_target: String,
    pub beta_priority: u8,
    pub ci_live_calls_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalCoverageTarget {
    pub target_id: String,
    pub competitions: Vec<String>,
    pub seasons_minimum: u8,
    pub requires_results: bool,
    pub requires_odds_snapshots: bool,
    pub requires_lineups_events: bool,
    pub use_for_beta_evaluation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderDesktopSurface {
    pub provider_health_panel: bool,
    pub credential_status_panel: bool,
    pub historical_coverage_panel: bool,
    pub adapter_gap_panel: bool,
    pub live_fetch_button_enabled: bool,
    pub manual_manifest_import_enabled: bool,
    pub paper_only_banner_required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderDataBetaAcceptance {
    pub provider_matrix_added: bool,
    pub historical_coverage_targets_added: bool,
    pub credential_modes_declared: bool,
    pub desktop_source_panel_declared: bool,
    pub no_ci_network_calls: bool,
    pub no_credentials_in_repo: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderDataBetaReadinessReport {
    pub schema: String,
    pub matrix_id: String,
    pub ok: bool,
    pub provider_count: usize,
    pub priority_one_provider_count: usize,
    pub credential_env_vars: Vec<String>,
    pub support_counts: BTreeMap<String, usize>,
    pub historical_target_count: usize,
    pub desktop_ready_for_source_panel: bool,
    pub beta_blockers: Vec<String>,
}

pub fn parse_provider_data_beta_matrix(text: &str) -> Result<ProviderDataBetaMatrix, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_provider_data_beta_matrix_text(text: &str) -> Result<ProviderDataBetaReadinessReport, String> {
    let matrix = parse_provider_data_beta_matrix(text)
        .map_err(|err| format!("parse provider data beta matrix: {}", err))?;
    Ok(validate_provider_data_beta_matrix(&matrix))
}

pub fn validate_provider_data_beta_matrix(matrix: &ProviderDataBetaMatrix) -> ProviderDataBetaReadinessReport {
    let mut blockers = Vec::new();
    if matrix.schema != "omnibet.provider_data_beta_matrix.v253" {
        blockers.push(format!("unexpected schema: {}", matrix.schema));
    }
    if !matrix.paper_only || matrix.network_calls_allowed_in_ci || matrix.credentials_stored_in_repo {
        blockers.push("matrix must be paper-only, offline in CI, and store no credentials".to_string());
    }
    if matrix.providers.len() < 4 {
        blockers.push("actual beta needs at least four provider/source candidates".to_string());
    }
    if matrix.historical_coverage_targets.is_empty() {
        blockers.push("historical coverage targets are required".to_string());
    }
    if !matrix.desktop_surface.provider_health_panel
        || !matrix.desktop_surface.credential_status_panel
        || !matrix.desktop_surface.historical_coverage_panel
        || !matrix.desktop_surface.adapter_gap_panel
        || matrix.desktop_surface.live_fetch_button_enabled
        || !matrix.desktop_surface.manual_manifest_import_enabled
        || !matrix.desktop_surface.paper_only_banner_required
    {
        blockers.push("desktop source surface must be read-only, visible, and paper-only".to_string());
    }
    if !matrix.acceptance.provider_matrix_added
        || !matrix.acceptance.historical_coverage_targets_added
        || !matrix.acceptance.credential_modes_declared
        || !matrix.acceptance.desktop_source_panel_declared
        || !matrix.acceptance.no_ci_network_calls
        || !matrix.acceptance.no_credentials_in_repo
    {
        blockers.push("acceptance flags are incomplete".to_string());
    }

    let mut provider_ids = std::collections::BTreeSet::new();
    let mut credential_env_vars = Vec::new();
    let mut support_counts = BTreeMap::from([
        ("fixtures".to_string(), 0usize),
        ("odds_snapshots".to_string(), 0usize),
        ("results".to_string(), 0usize),
        ("lineups_events".to_string(), 0usize),
    ]);
    let mut priority_one_provider_count = 0usize;

    for provider in &matrix.providers {
        if !provider_ids.insert(provider.provider_id.clone()) {
            blockers.push(format!("duplicate provider id: {}", provider.provider_id));
        }
        if provider.beta_priority == 0 {
            blockers.push(format!("provider beta priority must be non-zero: {}", provider.provider_id));
        }
        if provider.beta_priority == 1 {
            priority_one_provider_count += 1;
        }
        if provider.ci_live_calls_allowed {
            blockers.push(format!("CI live calls must stay disabled: {}", provider.provider_id));
        }
        if provider.credential_mode.contains("environment_variable") {
            match &provider.credential_env_var {
                Some(name) if !name.trim().is_empty() => credential_env_vars.push(name.clone()),
                _ => blockers.push(format!("missing credential env var: {}", provider.provider_id)),
            }
        }
        if provider.supports_fixtures {
            *support_counts.get_mut("fixtures").expect("fixtures count") += 1;
        }
        if provider.supports_odds_snapshots {
            *support_counts.get_mut("odds_snapshots").expect("odds count") += 1;
        }
        if provider.supports_results {
            *support_counts.get_mut("results").expect("results count") += 1;
        }
        if provider.supports_lineups_events {
            *support_counts.get_mut("lineups_events").expect("events count") += 1;
        }
    }

    if support_counts["odds_snapshots"] == 0 || support_counts["results"] == 0 {
        blockers.push("actual beta requires both odds snapshots and results sources".to_string());
    }
    if priority_one_provider_count < 2 {
        blockers.push("actual beta needs at least two priority-one sources".to_string());
    }
    for target in &matrix.historical_coverage_targets {
        if target.competitions.is_empty() || target.seasons_minimum == 0 {
            blockers.push(format!("invalid historical coverage target: {}", target.target_id));
        }
        if target.use_for_beta_evaluation && (!target.requires_results || !target.requires_odds_snapshots) {
            blockers.push(format!("beta evaluation target must require results and odds: {}", target.target_id));
        }
    }

    ProviderDataBetaReadinessReport {
        schema: "omnibet.provider_data_beta_readiness_report.v253".to_string(),
        matrix_id: matrix.matrix_id.clone(),
        ok: blockers.is_empty(),
        provider_count: matrix.providers.len(),
        priority_one_provider_count,
        credential_env_vars,
        support_counts,
        historical_target_count: matrix.historical_coverage_targets.len(),
        desktop_ready_for_source_panel: blockers.iter().all(|blocker| !blocker.contains("desktop source surface")),
        beta_blockers: blockers,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_provider_data_beta_matrix() {
        let report = validate_provider_data_beta_matrix_text(include_str!("../../configs/provider_data_beta_matrix.v253.json"))
            .expect("validate matrix");
        assert!(report.ok, "{:?}", report.beta_blockers);
        assert_eq!(report.provider_count, 5);
        assert_eq!(report.priority_one_provider_count, 2);
        assert!(report.credential_env_vars.contains(&"THE_ODDS_API_KEY".to_string()));
        assert!(report.credential_env_vars.contains(&"API_FOOTBALL_KEY".to_string()));
        assert!(report.support_counts["odds_snapshots"] >= 2);
        assert!(report.support_counts["results"] >= 3);
        assert_eq!(report.historical_target_count, 2);
        assert!(report.desktop_ready_for_source_panel);
    }

    #[test]
    fn rejects_network_credentials_and_weak_coverage() {
        let mut matrix = parse_provider_data_beta_matrix(include_str!("../../configs/provider_data_beta_matrix.v253.json"))
            .expect("parse matrix");
        matrix.network_calls_allowed_in_ci = true;
        matrix.credentials_stored_in_repo = true;
        matrix.providers[0].ci_live_calls_allowed = true;
        matrix.providers[0].credential_env_var = None;
        matrix.historical_coverage_targets[0].requires_odds_snapshots = false;
        let report = validate_provider_data_beta_matrix(&matrix);
        assert!(!report.ok);
        assert!(report.beta_blockers.iter().any(|blocker| blocker.contains("offline in CI")));
        assert!(report.beta_blockers.iter().any(|blocker| blocker.contains("CI live calls")));
        assert!(report.beta_blockers.iter().any(|blocker| blocker.contains("missing credential env var")));
        assert!(report.beta_blockers.iter().any(|blocker| blocker.contains("beta evaluation target")));
    }
}
