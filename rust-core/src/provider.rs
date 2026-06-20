use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderRuntimeContract {
    pub schema: String,
    pub goal: String,
    pub network_policy: NetworkPolicy,
    pub providers: Vec<ProviderDefinition>,
    pub snapshot_contract: SnapshotContract,
    pub adapter_stages: Vec<String>,
    pub canonical_outputs: Vec<String>,
    pub acceptance: ProviderAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct NetworkPolicy {
    pub ci_live_calls_allowed: bool,
    pub providers_disabled_by_default: bool,
    pub manual_enable_required: bool,
    pub credential_values_stored: bool,
    pub credential_values_displayed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderDefinition {
    pub provider_id: String,
    pub label: String,
    pub role: String,
    pub credential_env: String,
    pub enabled_by_default: bool,
    pub supports_live: bool,
    pub supports_historical: bool,
    pub supports_odds: bool,
    pub supports_fixtures: bool,
    pub supports_lineups: bool,
    pub supports_events: bool,
    pub supports_player_props: bool,
    pub planned_payloads: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SnapshotContract {
    pub required_fields: Vec<String>,
    pub default_payload_codec: String,
    pub sample_payload_codec: String,
    pub raw_payload_retention_days_default: u32,
    pub payload_hash_required: bool,
    pub observed_at_required: bool,
    pub prediction_time_boundary_required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderAcceptance {
    pub rust_provider_metadata_types: bool,
    pub credential_status_only: bool,
    pub no_live_calls_in_ci: bool,
    pub providers_disabled_by_default: bool,
    pub source_capabilities_declared: bool,
    pub snapshot_manifest_declared: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderStatus {
    pub provider_id: String,
    pub label: String,
    pub enabled: bool,
    pub credential_env: String,
    pub credential_status_only: CredentialStatus,
    pub credential_value_displayed: bool,
    pub manual_enable_required: bool,
    pub ci_live_calls_allowed: bool,
    pub capabilities: ProviderCapabilities,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum CredentialStatus {
    Present,
    Missing,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderCapabilities {
    pub live: bool,
    pub historical: bool,
    pub odds: bool,
    pub fixtures: bool,
    pub lineups: bool,
    pub events: bool,
    pub player_props: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SourceSnapshotManifest {
    pub source_id: String,
    pub request_kind: String,
    pub captured_at: String,
    pub observed_at: String,
    pub payload_sha256: String,
    pub payload_codec: String,
    pub payload_path: String,
    pub credential_values_stored: bool,
    pub external_call_performed: bool,
}

pub fn parse_provider_runtime_contract(text: &str) -> Result<ProviderRuntimeContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn sha256_text(text: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn provider_statuses(
    contract: &ProviderRuntimeContract,
    env: &BTreeMap<String, String>,
) -> Vec<ProviderStatus> {
    contract
        .providers
        .iter()
        .map(|provider| ProviderStatus {
            provider_id: provider.provider_id.clone(),
            label: provider.label.clone(),
            enabled: false,
            credential_env: provider.credential_env.clone(),
            credential_status_only: if env.contains_key(&provider.credential_env) {
                CredentialStatus::Present
            } else {
                CredentialStatus::Missing
            },
            credential_value_displayed: false,
            manual_enable_required: contract.network_policy.manual_enable_required,
            ci_live_calls_allowed: contract.network_policy.ci_live_calls_allowed,
            capabilities: ProviderCapabilities {
                live: provider.supports_live,
                historical: provider.supports_historical,
                odds: provider.supports_odds,
                fixtures: provider.supports_fixtures,
                lineups: provider.supports_lineups,
                events: provider.supports_events,
                player_props: provider.supports_player_props,
            },
        })
        .collect()
}

pub fn build_sample_snapshot_manifest(
    source_id: &str,
    request_kind: &str,
    observed_at: &str,
    payload_path: &str,
    payload_text: &str,
) -> SourceSnapshotManifest {
    SourceSnapshotManifest {
        source_id: source_id.to_string(),
        request_kind: request_kind.to_string(),
        captured_at: observed_at.to_string(),
        observed_at: observed_at.to_string(),
        payload_sha256: sha256_text(payload_text),
        payload_codec: "json".to_string(),
        payload_path: payload_path.to_string(),
        credential_values_stored: false,
        external_call_performed: false,
    }
}

pub fn validate_provider_runtime_contract(contract: &ProviderRuntimeContract) -> Result<(), String> {
    if contract.schema != "omnibet.provider_runtime.v234" {
        return Err(format!("unexpected provider runtime schema: {}", contract.schema));
    }
    if contract.network_policy.ci_live_calls_allowed {
        return Err("CI live calls must remain disabled".to_string());
    }
    if !contract.network_policy.providers_disabled_by_default {
        return Err("providers must be disabled by default".to_string());
    }
    if !contract.network_policy.manual_enable_required {
        return Err("manual enable must be required".to_string());
    }
    if contract.network_policy.credential_values_stored || contract.network_policy.credential_values_displayed {
        return Err("credential values must never be stored or displayed".to_string());
    }
    if contract.providers.len() < 4 {
        return Err("expected at least four provider definitions".to_string());
    }
    for provider in &contract.providers {
        if provider.enabled_by_default {
            return Err(format!("provider enabled by default: {}", provider.provider_id));
        }
        if provider.credential_env.trim().is_empty() {
            return Err(format!("missing credential env for {}", provider.provider_id));
        }
        if provider.planned_payloads.is_empty() {
            return Err(format!("missing planned payloads for {}", provider.provider_id));
        }
    }
    for required in ["source_id", "request_kind", "captured_at", "observed_at", "payload_sha256", "payload_codec", "payload_path"] {
        if !contract.snapshot_contract.required_fields.iter().any(|x| x == required) {
            return Err(format!("snapshot required field missing: {}", required));
        }
    }
    if !contract.snapshot_contract.payload_hash_required || !contract.snapshot_contract.observed_at_required {
        return Err("snapshot hash and observed_at must be required".to_string());
    }
    if !contract.acceptance.credential_status_only || !contract.acceptance.no_live_calls_in_ci {
        return Err("provider acceptance safety flags are not set".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_provider_runtime_contract() {
        let text = include_str!("../../configs/provider_runtime.v234.json");
        let contract = parse_provider_runtime_contract(text).expect("parse provider contract");
        validate_provider_runtime_contract(&contract).expect("validate provider contract");
        assert!(contract.providers.iter().any(|p| p.provider_id == "the_odds_api"));
        assert!(contract.providers.iter().any(|p| p.provider_id == "api_football"));
    }

    #[test]
    fn provider_status_never_exposes_credential_value() {
        let text = include_str!("../../configs/provider_runtime.v234.json");
        let contract = parse_provider_runtime_contract(text).expect("parse provider contract");
        let mut env = BTreeMap::new();
        env.insert("THE_ODDS_API_KEY".to_string(), "secret-do-not-display".to_string());
        let statuses = provider_statuses(&contract, &env);
        let odds = statuses.iter().find(|s| s.provider_id == "the_odds_api").expect("odds status");
        assert_eq!(odds.credential_status_only, CredentialStatus::Present);
        assert!(!odds.credential_value_displayed);
        assert!(!odds.enabled);
        assert!(!odds.ci_live_calls_allowed);
    }

    #[test]
    fn sample_snapshot_manifest_is_hashed_and_offline() {
        let manifest = build_sample_snapshot_manifest(
            "the_odds_api",
            "event_markets",
            "2026-06-20T00:00:00Z",
            "data/samples/the_odds_api_event_markets_sample.json",
            "{\"ok\":true}",
        );
        assert_eq!(manifest.payload_sha256, sha256_text("{\"ok\":true}"));
        assert!(!manifest.credential_values_stored);
        assert!(!manifest.external_call_performed);
    }
}
