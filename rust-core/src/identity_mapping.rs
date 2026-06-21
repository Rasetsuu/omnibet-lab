use crate::provider::{
    parse_api_football_live_state_sample, parse_the_odds_api_event_markets_sample,
    ApiFootballParseOutput, ProviderFixtureSnapshot, ProviderLineupPlayerSnapshot,
    ProviderOddsSnapshot, TheOddsApiParseOutput,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum IdentityKind {
    Competition,
    Fixture,
    Team,
    Player,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IdentityMappingContract {
    pub schema: String,
    pub goal: String,
    pub promotion_policy: IdentityPromotionPolicy,
    pub canonical_entities: Vec<CanonicalIdentity>,
    pub provider_aliases: Vec<ProviderIdentityAlias>,
    pub expected_offline_preview: ExpectedIdentityPreview,
    pub acceptance: IdentityMappingAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IdentityPromotionPolicy {
    pub preview_only: bool,
    pub automatic_unknown_identity_promotion_allowed: bool,
    pub provider_alias_required: bool,
    pub fixture_identity_required_before_match_fact_promotion: bool,
    pub team_identity_required_before_team_fact_promotion: bool,
    pub player_identity_required_before_player_fact_promotion: bool,
    pub review_required_for_unmapped_identities: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonicalIdentity {
    pub canonical_id: String,
    pub entity_kind: IdentityKind,
    pub display_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderIdentityAlias {
    pub provider_id: String,
    pub entity_kind: IdentityKind,
    pub provider_entity_id: Option<String>,
    pub display_name: String,
    pub canonical_id: String,
    pub confidence: String,
    pub review_required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ExpectedIdentityPreview {
    pub fixture_identity_refs: usize,
    pub team_identity_refs: usize,
    pub player_identity_refs: usize,
    pub total_identity_refs: usize,
    pub resolved_identity_refs: usize,
    pub review_identity_refs: usize,
    pub blocked_promotions: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IdentityMappingAcceptance {
    pub rust_identity_preview_added: bool,
    pub provider_fixture_ids_resolve: bool,
    pub provider_team_ids_resolve: bool,
    pub provider_player_ids_resolve: bool,
    pub name_only_player_prop_identity_resolves_when_alias_exists: bool,
    pub unknown_identity_promotion_forbidden: bool,
    pub preview_only: bool,
    pub python_smoke_added: bool,
    pub ci_workflow_added: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub struct ProviderIdentityRef {
    pub provider_id: String,
    pub entity_kind: IdentityKind,
    pub provider_entity_id: Option<String>,
    pub display_name: String,
    pub source_context: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum IdentityResolutionStatus {
    Resolved,
    NeedsReview,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IdentityResolution {
    pub provider_id: String,
    pub entity_kind: IdentityKind,
    pub provider_entity_id: Option<String>,
    pub display_name: String,
    pub canonical_id: Option<String>,
    pub status: IdentityResolutionStatus,
    pub review_required: bool,
    pub promotion_allowed: bool,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IdentityMappingPreview {
    pub schema: String,
    pub preview_id: String,
    pub created_at: String,
    pub fixture_refs: usize,
    pub team_refs: usize,
    pub player_refs: usize,
    pub total_refs: usize,
    pub resolved_count: usize,
    pub review_count: usize,
    pub blocked_promotions: usize,
    pub automatic_unknown_identity_promotion_allowed: bool,
    pub resolved_rows: Vec<IdentityResolution>,
    pub review_rows: Vec<IdentityResolution>,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct AliasKey {
    provider_id: String,
    entity_kind: IdentityKind,
    provider_entity_id: Option<String>,
    normalized_name: String,
}

pub fn parse_identity_mapping_contract(text: &str) -> Result<IdentityMappingContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_identity_mapping_contract(contract: &IdentityMappingContract) -> Result<(), String> {
    if contract.schema != "omnibet.identity_mapping_preview.v239" {
        return Err(format!("unexpected identity mapping schema: {}", contract.schema));
    }
    let policy = &contract.promotion_policy;
    if !policy.preview_only {
        return Err("identity mapping must remain preview-only".to_string());
    }
    if policy.automatic_unknown_identity_promotion_allowed {
        return Err("unknown identity promotion must be forbidden".to_string());
    }
    if !policy.provider_alias_required || !policy.review_required_for_unmapped_identities {
        return Err("provider aliases and review for unmapped identities are required".to_string());
    }
    if !policy.fixture_identity_required_before_match_fact_promotion
        || !policy.team_identity_required_before_team_fact_promotion
        || !policy.player_identity_required_before_player_fact_promotion
    {
        return Err("fixture/team/player identity gates are required".to_string());
    }

    let canonical = contract
        .canonical_entities
        .iter()
        .map(|row| row.canonical_id.as_str())
        .collect::<BTreeSet<_>>();
    for alias in &contract.provider_aliases {
        if alias.review_required {
            return Err(format!("resolved identity alias should not require review: {}", alias.display_name));
        }
        if !canonical.contains(alias.canonical_id.as_str()) {
            return Err(format!("identity alias references missing canonical id: {}", alias.canonical_id));
        }
    }
    if !contract.provider_aliases.iter().any(|row| row.provider_id == "the_odds_api" && row.entity_kind == IdentityKind::Player && row.provider_entity_id.is_none()) {
        return Err("name-only player prop alias is required for The Odds API sample".to_string());
    }
    Ok(())
}

pub fn build_identity_refs_from_samples(
    odds: &TheOddsApiParseOutput,
    football: &ApiFootballParseOutput,
) -> Vec<ProviderIdentityRef> {
    let mut refs = BTreeSet::new();
    push_fixture_ref(&mut refs, &odds.fixture);
    push_fixture_ref(&mut refs, &football.fixture);
    push_fixture_teams(&mut refs, &odds.fixture);
    push_fixture_teams(&mut refs, &football.fixture);
    for lineup in &football.lineups {
        push_lineup_player_ref(&mut refs, lineup);
        if let (Some(team_id), Some(team_name)) = (&lineup.team_id, &lineup.team_name) {
            refs.insert(ProviderIdentityRef {
                provider_id: lineup.source_id.clone(),
                entity_kind: IdentityKind::Team,
                provider_entity_id: Some(team_id.clone()),
                display_name: team_name.clone(),
                source_context: "lineup_team".to_string(),
            });
        }
    }
    for event in &football.events {
        if let (Some(team_id), Some(team_name)) = (&event.team_id, &event.team_name) {
            refs.insert(ProviderIdentityRef {
                provider_id: event.source_id.clone(),
                entity_kind: IdentityKind::Team,
                provider_entity_id: Some(team_id.clone()),
                display_name: team_name.clone(),
                source_context: "event_team".to_string(),
            });
        }
        if let (Some(player_id), Some(player_name)) = (&event.player_id, &event.player_name) {
            refs.insert(ProviderIdentityRef {
                provider_id: event.source_id.clone(),
                entity_kind: IdentityKind::Player,
                provider_entity_id: Some(player_id.clone()),
                display_name: player_name.clone(),
                source_context: "event_player".to_string(),
            });
        }
        if let (Some(player_id), Some(player_name)) = (&event.assist_player_id, &event.assist_player_name) {
            refs.insert(ProviderIdentityRef {
                provider_id: event.source_id.clone(),
                entity_kind: IdentityKind::Player,
                provider_entity_id: Some(player_id.clone()),
                display_name: player_name.clone(),
                source_context: "event_assist".to_string(),
            });
        }
    }
    for odds_row in &odds.odds {
        push_odds_participant_ref(&mut refs, odds_row);
    }
    refs.into_iter().collect()
}

pub fn build_identity_mapping_preview(
    contract: &IdentityMappingContract,
    refs: &[ProviderIdentityRef],
    preview_id: &str,
    created_at: &str,
) -> IdentityMappingPreview {
    let mut resolved_rows = Vec::new();
    let mut review_rows = Vec::new();
    for identity_ref in refs {
        let resolution = resolve_identity(contract, identity_ref);
        if resolution.promotion_allowed {
            resolved_rows.push(resolution);
        } else {
            review_rows.push(resolution);
        }
    }
    let fixture_refs = refs.iter().filter(|row| row.entity_kind == IdentityKind::Fixture).count();
    let team_refs = refs.iter().filter(|row| row.entity_kind == IdentityKind::Team).count();
    let player_refs = refs.iter().filter(|row| row.entity_kind == IdentityKind::Player).count();
    IdentityMappingPreview {
        schema: "omnibet.identity_mapping_preview.v239".to_string(),
        preview_id: preview_id.to_string(),
        created_at: created_at.to_string(),
        fixture_refs,
        team_refs,
        player_refs,
        total_refs: refs.len(),
        resolved_count: resolved_rows.len(),
        review_count: review_rows.len(),
        blocked_promotions: review_rows.len(),
        automatic_unknown_identity_promotion_allowed: false,
        resolved_rows,
        review_rows,
    }
}

pub fn build_identity_preview_from_offline_samples(
    contract_text: &str,
    odds_sample_text: &str,
    football_sample_text: &str,
    created_at: &str,
) -> Result<IdentityMappingPreview, String> {
    let contract = parse_identity_mapping_contract(contract_text)
        .map_err(|e| format!("parse identity contract: {}", e))?;
    validate_identity_mapping_contract(&contract)?;
    let odds = parse_the_odds_api_event_markets_sample(odds_sample_text, created_at)?;
    let football = parse_api_football_live_state_sample(football_sample_text, created_at)?;
    let refs = build_identity_refs_from_samples(&odds, &football);
    Ok(build_identity_mapping_preview(
        &contract,
        &refs,
        "v239_offline_identity_mapping_preview",
        created_at,
    ))
}

pub fn resolve_identity(
    contract: &IdentityMappingContract,
    identity_ref: &ProviderIdentityRef,
) -> IdentityResolution {
    let alias_by_exact_key = contract
        .provider_aliases
        .iter()
        .map(|alias| (alias_key(alias.provider_id.clone(), alias.entity_kind.clone(), alias.provider_entity_id.clone(), &alias.display_name), alias))
        .collect::<BTreeMap<_, _>>();

    let exact_key = AliasKey {
        provider_id: identity_ref.provider_id.clone(),
        entity_kind: identity_ref.entity_kind.clone(),
        provider_entity_id: identity_ref.provider_entity_id.clone(),
        normalized_name: normalize_name(&identity_ref.display_name),
    };
    let name_only_key = AliasKey {
        provider_id: identity_ref.provider_id.clone(),
        entity_kind: identity_ref.entity_kind.clone(),
        provider_entity_id: None,
        normalized_name: normalize_name(&identity_ref.display_name),
    };
    let alias = alias_by_exact_key
        .get(&exact_key)
        .or_else(|| alias_by_exact_key.get(&name_only_key));

    if let Some(alias) = alias {
        return IdentityResolution {
            provider_id: identity_ref.provider_id.clone(),
            entity_kind: identity_ref.entity_kind.clone(),
            provider_entity_id: identity_ref.provider_entity_id.clone(),
            display_name: identity_ref.display_name.clone(),
            canonical_id: Some(alias.canonical_id.clone()),
            status: IdentityResolutionStatus::Resolved,
            review_required: false,
            promotion_allowed: true,
            reason: None,
        };
    }

    IdentityResolution {
        provider_id: identity_ref.provider_id.clone(),
        entity_kind: identity_ref.entity_kind.clone(),
        provider_entity_id: identity_ref.provider_entity_id.clone(),
        display_name: identity_ref.display_name.clone(),
        canonical_id: None,
        status: IdentityResolutionStatus::NeedsReview,
        review_required: true,
        promotion_allowed: false,
        reason: Some("unmapped_provider_identity".to_string()),
    }
}

fn alias_key(
    provider_id: String,
    entity_kind: IdentityKind,
    provider_entity_id: Option<String>,
    display_name: &str,
) -> AliasKey {
    AliasKey {
        provider_id,
        entity_kind,
        provider_entity_id,
        normalized_name: normalize_name(display_name),
    }
}

fn normalize_name(name: &str) -> String {
    name.chars()
        .filter(|c| c.is_ascii_alphanumeric())
        .flat_map(|c| c.to_lowercase())
        .collect()
}

fn push_fixture_ref(refs: &mut BTreeSet<ProviderIdentityRef>, fixture: &ProviderFixtureSnapshot) {
    let display_name = match (&fixture.home_team_name, &fixture.away_team_name) {
        (Some(home), Some(away)) => format!("{} vs {}", home, away),
        _ => fixture.source_event_id.clone(),
    };
    refs.insert(ProviderIdentityRef {
        provider_id: fixture.source_id.clone(),
        entity_kind: IdentityKind::Fixture,
        provider_entity_id: Some(fixture.source_event_id.clone()),
        display_name,
        source_context: "fixture".to_string(),
    });
}

fn push_fixture_teams(refs: &mut BTreeSet<ProviderIdentityRef>, fixture: &ProviderFixtureSnapshot) {
    if let Some(name) = &fixture.home_team_name {
        refs.insert(ProviderIdentityRef {
            provider_id: fixture.source_id.clone(),
            entity_kind: IdentityKind::Team,
            provider_entity_id: fixture.home_team_id.clone(),
            display_name: name.clone(),
            source_context: "fixture_home_team".to_string(),
        });
    }
    if let Some(name) = &fixture.away_team_name {
        refs.insert(ProviderIdentityRef {
            provider_id: fixture.source_id.clone(),
            entity_kind: IdentityKind::Team,
            provider_entity_id: fixture.away_team_id.clone(),
            display_name: name.clone(),
            source_context: "fixture_away_team".to_string(),
        });
    }
}

fn push_lineup_player_ref(refs: &mut BTreeSet<ProviderIdentityRef>, lineup: &ProviderLineupPlayerSnapshot) {
    if let Some(name) = &lineup.player_name {
        refs.insert(ProviderIdentityRef {
            provider_id: lineup.source_id.clone(),
            entity_kind: IdentityKind::Player,
            provider_entity_id: lineup.player_id.clone(),
            display_name: name.clone(),
            source_context: if lineup.started { "lineup_start" } else { "lineup_bench" }.to_string(),
        });
    }
}

fn push_odds_participant_ref(refs: &mut BTreeSet<ProviderIdentityRef>, odds: &ProviderOddsSnapshot) {
    if odds.market_key.contains("player") {
        if let Some(participant) = &odds.participant {
            refs.insert(ProviderIdentityRef {
                provider_id: odds.source_id.clone(),
                entity_kind: IdentityKind::Player,
                provider_entity_id: None,
                display_name: participant.clone(),
                source_context: "odds_player_prop_participant".to_string(),
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_identity_preview_from_offline_samples() {
        let preview = build_identity_preview_from_offline_samples(
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build identity preview");
        assert_eq!(preview.schema, "omnibet.identity_mapping_preview.v239");
        assert_eq!(preview.fixture_refs, 2);
        assert_eq!(preview.team_refs, 4);
        assert_eq!(preview.player_refs, 9);
        assert_eq!(preview.total_refs, 15);
        assert_eq!(preview.resolved_count, 15);
        assert_eq!(preview.review_count, 0);
        assert!(!preview.automatic_unknown_identity_promotion_allowed);
        assert!(preview.resolved_rows.iter().any(|row| row.provider_id == "the_odds_api" && row.entity_kind == IdentityKind::Player && row.display_name == "Kylian Mbappe" && row.canonical_id.as_deref() == Some("player_kylian_mbappe")));
    }

    #[test]
    fn unknown_identity_needs_review() {
        let contract = parse_identity_mapping_contract(include_str!("../../configs/identity_mapping_preview.v239.json"))
            .expect("parse identity contract");
        let identity_ref = ProviderIdentityRef {
            provider_id: "api_football".to_string(),
            entity_kind: IdentityKind::Player,
            provider_entity_id: Some("999999".to_string()),
            display_name: "Unknown Trialist".to_string(),
            source_context: "test".to_string(),
        };
        let resolution = resolve_identity(&contract, &identity_ref);
        assert_eq!(resolution.status, IdentityResolutionStatus::NeedsReview);
        assert!(resolution.review_required);
        assert!(!resolution.promotion_allowed);
        assert_eq!(resolution.reason.as_deref(), Some("unmapped_provider_identity"));
    }
}
