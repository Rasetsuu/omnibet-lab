use serde::{Deserialize, Serialize};
use serde_json::Value;
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

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProviderFixtureSnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub sport_key: Option<String>,
    pub competition_name: Option<String>,
    pub season: Option<i64>,
    pub commence_time: Option<String>,
    pub status_short: Option<String>,
    pub elapsed: Option<i64>,
    pub home_team_id: Option<String>,
    pub away_team_id: Option<String>,
    pub home_team_name: Option<String>,
    pub away_team_name: Option<String>,
    pub home_goals: Option<i64>,
    pub away_goals: Option<i64>,
    pub venue_name: Option<String>,
    pub observed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProviderOddsSnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub bookmaker_key: String,
    pub bookmaker_title: Option<String>,
    pub market_key: String,
    pub selection: String,
    pub odds_decimal: f64,
    pub line: Option<f64>,
    pub participant: Option<String>,
    pub last_update: Option<String>,
    pub observed_at: String,
    pub is_live: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderMarketDiscoverySnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub bookmaker_key: String,
    pub market_key: String,
    pub outcome_count: usize,
    pub has_line: bool,
    pub canonical_hint: Option<String>,
    pub needs_mapping_review: bool,
    pub observed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderEventSnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub minute: Option<i64>,
    pub extra_minute: Option<i64>,
    pub team_id: Option<String>,
    pub team_name: Option<String>,
    pub player_id: Option<String>,
    pub player_name: Option<String>,
    pub assist_player_id: Option<String>,
    pub assist_player_name: Option<String>,
    pub event_type: Option<String>,
    pub detail: Option<String>,
    pub observed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderLineupPlayerSnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub team_id: Option<String>,
    pub team_name: Option<String>,
    pub formation: Option<String>,
    pub player_id: Option<String>,
    pub player_name: Option<String>,
    pub shirt_number: Option<i64>,
    pub position: Option<String>,
    pub grid: Option<String>,
    pub started: bool,
    pub observed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProviderTeamStatisticSnapshot {
    pub source_id: String,
    pub source_event_id: String,
    pub team_id: Option<String>,
    pub team_name: Option<String>,
    pub statistic_type: String,
    pub value_text: Option<String>,
    pub value_number: Option<f64>,
    pub observed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TheOddsApiParseOutput {
    pub manifest: SourceSnapshotManifest,
    pub fixture: ProviderFixtureSnapshot,
    pub odds: Vec<ProviderOddsSnapshot>,
    pub markets: Vec<ProviderMarketDiscoverySnapshot>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ApiFootballParseOutput {
    pub manifest: SourceSnapshotManifest,
    pub fixture: ProviderFixtureSnapshot,
    pub events: Vec<ProviderEventSnapshot>,
    pub lineups: Vec<ProviderLineupPlayerSnapshot>,
    pub statistics: Vec<ProviderTeamStatisticSnapshot>,
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

fn field_str(value: &Value, key: &str) -> Option<String> {
    value.get(key).and_then(Value::as_str).map(str::to_string)
}

fn field_i64(value: &Value, key: &str) -> Option<i64> {
    value.get(key).and_then(Value::as_i64)
}

fn field_f64(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn id_to_string(value: Option<&Value>) -> Option<String> {
    match value? {
        Value::String(s) => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        _ => None,
    }
}

fn canonical_market_hint(provider_key: &str) -> Option<String> {
    match provider_key {
        "h2h" => Some("match_result_1x2".to_string()),
        "spreads" => Some("handicap".to_string()),
        "totals" => Some("total_goals".to_string()),
        "corners" => Some("total_corners".to_string()),
        "shots_on_target" => Some("team_shots_on_target".to_string()),
        "player_shots_on_target" => Some("player_shots_on_target".to_string()),
        _ => None,
    }
}

pub fn parse_the_odds_api_event_markets_sample(
    text: &str,
    observed_at: &str,
) -> Result<TheOddsApiParseOutput, String> {
    let root: Value = serde_json::from_str(text).map_err(|e| format!("parse The Odds API sample JSON: {}", e))?;
    let source_event_id = field_str(&root, "id").ok_or_else(|| "The Odds API sample missing id".to_string())?;
    let home_team = field_str(&root, "home_team");
    let away_team = field_str(&root, "away_team");
    let bookmakers = root
        .get("bookmakers")
        .and_then(Value::as_array)
        .ok_or_else(|| "The Odds API sample missing bookmakers array".to_string())?;

    let mut odds = Vec::new();
    let mut markets = Vec::new();
    for bookmaker in bookmakers {
        let bookmaker_key = field_str(bookmaker, "key").unwrap_or_else(|| "unknown_bookmaker".to_string());
        let bookmaker_title = field_str(bookmaker, "title");
        let bookmaker_markets = bookmaker.get("markets").and_then(Value::as_array).unwrap_or(&Vec::new());
        for market in bookmaker_markets {
            let market_key = field_str(market, "key").unwrap_or_else(|| "unknown_market".to_string());
            let outcomes = market.get("outcomes").and_then(Value::as_array).unwrap_or(&Vec::new());
            let has_line = outcomes.iter().any(|outcome| outcome.get("point").is_some());
            let canonical_hint = canonical_market_hint(&market_key);
            markets.push(ProviderMarketDiscoverySnapshot {
                source_id: "the_odds_api".to_string(),
                source_event_id: source_event_id.clone(),
                bookmaker_key: bookmaker_key.clone(),
                market_key: market_key.clone(),
                outcome_count: outcomes.len(),
                has_line,
                needs_mapping_review: canonical_hint.is_none(),
                canonical_hint,
                observed_at: observed_at.to_string(),
            });
            for outcome in outcomes {
                let selection = field_str(outcome, "name").unwrap_or_else(|| "unknown_selection".to_string());
                let odds_decimal = field_f64(outcome, "price").ok_or_else(|| {
                    format!("missing decimal price for {} {}", bookmaker_key, market_key)
                })?;
                odds.push(ProviderOddsSnapshot {
                    source_id: "the_odds_api".to_string(),
                    source_event_id: source_event_id.clone(),
                    bookmaker_key: bookmaker_key.clone(),
                    bookmaker_title: bookmaker_title.clone(),
                    market_key: market_key.clone(),
                    selection,
                    odds_decimal,
                    line: field_f64(outcome, "point"),
                    participant: field_str(outcome, "description"),
                    last_update: field_str(market, "last_update").or_else(|| field_str(bookmaker, "last_update")),
                    observed_at: observed_at.to_string(),
                    is_live: false,
                });
            }
        }
    }

    Ok(TheOddsApiParseOutput {
        manifest: build_sample_snapshot_manifest(
            "the_odds_api",
            "event_markets",
            observed_at,
            "data/samples/the_odds_api_event_markets_sample.json",
            text,
        ),
        fixture: ProviderFixtureSnapshot {
            source_id: "the_odds_api".to_string(),
            source_event_id,
            sport_key: field_str(&root, "sport_key"),
            competition_name: field_str(&root, "sport_title"),
            season: None,
            commence_time: field_str(&root, "commence_time"),
            status_short: None,
            elapsed: None,
            home_team_id: None,
            away_team_id: None,
            home_team_name: home_team,
            away_team_name: away_team,
            home_goals: None,
            away_goals: None,
            venue_name: None,
            observed_at: observed_at.to_string(),
        },
        odds,
        markets,
    })
}

pub fn parse_api_football_live_state_sample(
    text: &str,
    observed_at: &str,
) -> Result<ApiFootballParseOutput, String> {
    let root: Value = serde_json::from_str(text).map_err(|e| format!("parse API-Football sample JSON: {}", e))?;
    let response = root
        .get("response")
        .and_then(Value::as_array)
        .ok_or_else(|| "API-Football sample missing response array".to_string())?;
    let first = response.first().ok_or_else(|| "API-Football sample response is empty".to_string())?;
    let fixture = first.get("fixture").ok_or_else(|| "API-Football sample missing fixture".to_string())?;
    let league = first.get("league").unwrap_or(&Value::Null);
    let teams = first.get("teams").unwrap_or(&Value::Null);
    let home = teams.get("home").unwrap_or(&Value::Null);
    let away = teams.get("away").unwrap_or(&Value::Null);
    let goals = first.get("goals").unwrap_or(&Value::Null);
    let venue = fixture.get("venue").unwrap_or(&Value::Null);
    let status = fixture.get("status").unwrap_or(&Value::Null);
    let source_event_id = id_to_string(fixture.get("id")).ok_or_else(|| "API-Football fixture missing id".to_string())?;

    let events = first
        .get("events")
        .and_then(Value::as_array)
        .unwrap_or(&Vec::new())
        .iter()
        .map(|event| {
            let time = event.get("time").unwrap_or(&Value::Null);
            let team = event.get("team").unwrap_or(&Value::Null);
            let player = event.get("player").unwrap_or(&Value::Null);
            let assist = event.get("assist").unwrap_or(&Value::Null);
            ProviderEventSnapshot {
                source_id: "api_football".to_string(),
                source_event_id: source_event_id.clone(),
                minute: field_i64(time, "elapsed"),
                extra_minute: field_i64(time, "extra"),
                team_id: id_to_string(team.get("id")),
                team_name: field_str(team, "name"),
                player_id: id_to_string(player.get("id")),
                player_name: field_str(player, "name"),
                assist_player_id: id_to_string(assist.get("id")),
                assist_player_name: field_str(assist, "name"),
                event_type: field_str(event, "type"),
                detail: field_str(event, "detail"),
                observed_at: observed_at.to_string(),
            }
        })
        .collect::<Vec<_>>();

    let mut lineups = Vec::new();
    for lineup in first.get("lineups").and_then(Value::as_array).unwrap_or(&Vec::new()) {
        let team = lineup.get("team").unwrap_or(&Value::Null);
        let team_id = id_to_string(team.get("id"));
        let team_name = field_str(team, "name");
        let formation = field_str(lineup, "formation");
        for (list_key, started) in [("startXI", true), ("substitutes", false)] {
            for row in lineup.get(list_key).and_then(Value::as_array).unwrap_or(&Vec::new()) {
                let player = row.get("player").unwrap_or(&Value::Null);
                lineups.push(ProviderLineupPlayerSnapshot {
                    source_id: "api_football".to_string(),
                    source_event_id: source_event_id.clone(),
                    team_id: team_id.clone(),
                    team_name: team_name.clone(),
                    formation: formation.clone(),
                    player_id: id_to_string(player.get("id")),
                    player_name: field_str(player, "name"),
                    shirt_number: field_i64(player, "number"),
                    position: field_str(player, "pos"),
                    grid: field_str(player, "grid"),
                    started,
                    observed_at: observed_at.to_string(),
                });
            }
        }
    }

    let mut statistics = Vec::new();
    for team_stats in first.get("statistics").and_then(Value::as_array).unwrap_or(&Vec::new()) {
        let team = team_stats.get("team").unwrap_or(&Value::Null);
        for stat in team_stats.get("statistics").and_then(Value::as_array).unwrap_or(&Vec::new()) {
            let raw_value = stat.get("value");
            statistics.push(ProviderTeamStatisticSnapshot {
                source_id: "api_football".to_string(),
                source_event_id: source_event_id.clone(),
                team_id: id_to_string(team.get("id")),
                team_name: field_str(team, "name"),
                statistic_type: field_str(stat, "type").unwrap_or_else(|| "unknown".to_string()),
                value_text: raw_value.and_then(Value::as_str).map(str::to_string),
                value_number: raw_value.and_then(Value::as_f64),
                observed_at: observed_at.to_string(),
            });
        }
    }

    Ok(ApiFootballParseOutput {
        manifest: build_sample_snapshot_manifest(
            "api_football",
            "live_state",
            observed_at,
            "data/samples/api_football_live_state_sample.json",
            text,
        ),
        fixture: ProviderFixtureSnapshot {
            source_id: "api_football".to_string(),
            source_event_id,
            sport_key: None,
            competition_name: field_str(league, "name"),
            season: field_i64(league, "season"),
            commence_time: field_str(fixture, "date"),
            status_short: field_str(status, "short"),
            elapsed: field_i64(status, "elapsed"),
            home_team_id: id_to_string(home.get("id")),
            away_team_id: id_to_string(away.get("id")),
            home_team_name: field_str(home, "name"),
            away_team_name: field_str(away, "name"),
            home_goals: field_i64(goals, "home"),
            away_goals: field_i64(goals, "away"),
            venue_name: field_str(venue, "name"),
            observed_at: observed_at.to_string(),
        },
        events,
        lineups,
        statistics,
    })
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

    #[test]
    fn parses_the_odds_api_offline_provider_sample() {
        let text = include_str!("../../data/samples/the_odds_api_event_markets_sample.json");
        let parsed = parse_the_odds_api_event_markets_sample(text, "2026-06-16T18:02:00Z")
            .expect("parse The Odds API sample");
        assert_eq!(parsed.fixture.home_team_name.as_deref(), Some("France"));
        assert_eq!(parsed.fixture.away_team_name.as_deref(), Some("Senegal"));
        assert_eq!(parsed.markets.len(), 8);
        assert_eq!(parsed.odds.len(), 17);
        assert!(parsed.markets.iter().any(|m| m.market_key == "special_combo_unknown" && m.needs_mapping_review));
        assert!(parsed.odds.iter().any(|o| o.market_key == "player_shots_on_target" && o.participant.as_deref() == Some("Kylian Mbappe")));
        assert!(!parsed.manifest.external_call_performed);
        assert!(!parsed.manifest.credential_values_stored);
    }

    #[test]
    fn parses_api_football_offline_provider_sample() {
        let text = include_str!("../../data/samples/api_football_live_state_sample.json");
        let parsed = parse_api_football_live_state_sample(text, "2026-06-16T22:00:00Z")
            .expect("parse API-Football sample");
        assert_eq!(parsed.fixture.source_event_id, "123456");
        assert_eq!(parsed.fixture.status_short.as_deref(), Some("FT"));
        assert_eq!(parsed.fixture.home_goals, Some(2));
        assert_eq!(parsed.fixture.away_goals, Some(1));
        assert_eq!(parsed.events.len(), 4);
        assert_eq!(parsed.lineups.len(), 8);
        assert_eq!(parsed.statistics.len(), 12);
        assert!(parsed.events.iter().any(|e| e.player_name.as_deref() == Some("Kylian Mbappe") && e.event_type.as_deref() == Some("Goal")));
        assert!(parsed.lineups.iter().any(|p| p.player_name.as_deref() == Some("Olivier Giroud") && !p.started));
        assert!(!parsed.manifest.external_call_performed);
        assert!(!parsed.manifest.credential_values_stored);
    }
}
