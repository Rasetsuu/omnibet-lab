use crate::provider::ProviderMarketDiscoverySnapshot;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketRegistryContract {
    pub schema: String,
    pub goal: String,
    pub promotion_policy: MarketPromotionPolicy,
    pub canonical_markets: Vec<CanonicalMarket>,
    pub provider_aliases: Vec<ProviderMarketAlias>,
    pub review_queue_examples: Vec<MarketReviewExample>,
    pub acceptance: MarketRegistryAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketPromotionPolicy {
    pub automatic_unknown_market_promotion_allowed: bool,
    pub provider_alias_required: bool,
    pub settlement_rule_required: bool,
    pub market_family_required: bool,
    pub line_scope_required_for_line_markets: bool,
    pub player_scope_required_for_player_markets: bool,
    pub review_required_for_unmapped_markets: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonicalMarket {
    pub canonical_market_id: String,
    pub family: String,
    pub display_name: String,
    pub period: String,
    pub selection_scope: String,
    pub line_required: bool,
    pub player_required: bool,
    pub lineup_required: bool,
    pub settlement_rule: String,
    pub correlation_group: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProviderMarketAlias {
    pub provider_id: String,
    pub provider_market_key: String,
    pub canonical_market_id: String,
    pub confidence: String,
    pub review_required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketReviewExample {
    pub provider_id: String,
    pub provider_market_key: String,
    pub reason: String,
    pub automatic_promotion_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketRegistryAcceptance {
    pub known_provider_markets_resolve: bool,
    pub unknown_provider_markets_rejected: bool,
    pub unknown_provider_markets_reviewed: bool,
    pub player_markets_require_lineup: bool,
    pub line_markets_require_line: bool,
    pub settlement_rules_required: bool,
    pub rust_registry_types_added: bool,
    pub bronze_market_discovery_can_be_checked: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum MarketResolutionStatus {
    Resolved,
    NeedsReview,
    Rejected,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketResolution {
    pub provider_id: String,
    pub provider_market_key: String,
    pub status: MarketResolutionStatus,
    pub canonical_market_id: Option<String>,
    pub family: Option<String>,
    pub settlement_rule: Option<String>,
    pub line_required: bool,
    pub player_required: bool,
    pub lineup_required: bool,
    pub review_required: bool,
    pub reason: Option<String>,
}

pub fn parse_market_registry_contract(text: &str) -> Result<MarketRegistryContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_market_registry(contract: &MarketRegistryContract) -> Result<(), String> {
    if contract.schema != "omnibet.market_registry.v237" {
        return Err(format!("unexpected market registry schema: {}", contract.schema));
    }
    let policy = &contract.promotion_policy;
    if policy.automatic_unknown_market_promotion_allowed {
        return Err("unknown markets must not be auto-promoted".to_string());
    }
    if !policy.provider_alias_required || !policy.review_required_for_unmapped_markets {
        return Err("provider aliases and review queue are required".to_string());
    }
    if !policy.settlement_rule_required || !policy.market_family_required {
        return Err("settlement rule and market family are required".to_string());
    }
    if !policy.line_scope_required_for_line_markets || !policy.player_scope_required_for_player_markets {
        return Err("line/player scope guards are required".to_string());
    }

    let mut canonical = BTreeMap::new();
    for market in &contract.canonical_markets {
        if market.canonical_market_id.trim().is_empty() {
            return Err("canonical market id cannot be empty".to_string());
        }
        if market.family.trim().is_empty() {
            return Err(format!("canonical market {} missing family", market.canonical_market_id));
        }
        if market.settlement_rule.trim().is_empty() {
            return Err(format!("canonical market {} missing settlement rule", market.canonical_market_id));
        }
        canonical.insert(market.canonical_market_id.clone(), market);
    }
    if canonical.is_empty() {
        return Err("canonical market registry cannot be empty".to_string());
    }
    for alias in &contract.provider_aliases {
        if alias.review_required {
            return Err(format!("alias should not be pre-resolved if review is required: {}", alias.provider_market_key));
        }
        if !canonical.contains_key(&alias.canonical_market_id) {
            return Err(format!("alias references missing canonical market: {}", alias.canonical_market_id));
        }
    }
    if !canonical.values().any(|market| market.player_required && market.lineup_required) {
        return Err("at least one lineup-gated player market is required".to_string());
    }
    if !contract.review_queue_examples.iter().any(|row| row.provider_market_key == "special_combo_unknown" && !row.automatic_promotion_allowed) {
        return Err("special_combo_unknown must remain a review-only example".to_string());
    }
    Ok(())
}

pub fn resolve_provider_market(
    contract: &MarketRegistryContract,
    provider_id: &str,
    provider_market_key: &str,
) -> MarketResolution {
    let canonical_by_id = contract
        .canonical_markets
        .iter()
        .map(|market| (market.canonical_market_id.as_str(), market))
        .collect::<BTreeMap<_, _>>();

    let alias = contract.provider_aliases.iter().find(|alias| {
        alias.provider_id == provider_id && alias.provider_market_key == provider_market_key
    });

    if let Some(alias) = alias {
        if let Some(market) = canonical_by_id.get(alias.canonical_market_id.as_str()) {
            return MarketResolution {
                provider_id: provider_id.to_string(),
                provider_market_key: provider_market_key.to_string(),
                status: MarketResolutionStatus::Resolved,
                canonical_market_id: Some(market.canonical_market_id.clone()),
                family: Some(market.family.clone()),
                settlement_rule: Some(market.settlement_rule.clone()),
                line_required: market.line_required,
                player_required: market.player_required,
                lineup_required: market.lineup_required,
                review_required: false,
                reason: None,
            };
        }
    }

    MarketResolution {
        provider_id: provider_id.to_string(),
        provider_market_key: provider_market_key.to_string(),
        status: MarketResolutionStatus::NeedsReview,
        canonical_market_id: None,
        family: None,
        settlement_rule: None,
        line_required: false,
        player_required: false,
        lineup_required: false,
        review_required: true,
        reason: Some("unmapped_provider_market".to_string()),
    }
}

pub fn resolve_market_discovery_rows(
    contract: &MarketRegistryContract,
    rows: &[ProviderMarketDiscoverySnapshot],
) -> Vec<MarketResolution> {
    rows.iter()
        .map(|row| resolve_provider_market(contract, &row.source_id, &row.market_key))
        .collect()
}

pub fn promotion_allowed(resolution: &MarketResolution) -> bool {
    resolution.status == MarketResolutionStatus::Resolved
        && resolution.canonical_market_id.is_some()
        && resolution.settlement_rule.is_some()
        && !resolution.review_required
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provider::parse_the_odds_api_event_markets_sample;

    #[test]
    fn validates_market_registry_contract() {
        let text = include_str!("../../configs/market_registry.v237.json");
        let contract = parse_market_registry_contract(text).expect("parse registry");
        validate_market_registry(&contract).expect("validate registry");
    }

    #[test]
    fn resolves_known_the_odds_api_markets() {
        let contract = parse_market_registry_contract(include_str!("../../configs/market_registry.v237.json"))
            .expect("parse registry");
        let result = resolve_provider_market(&contract, "the_odds_api", "totals");
        assert_eq!(result.status, MarketResolutionStatus::Resolved);
        assert_eq!(result.canonical_market_id.as_deref(), Some("total_goals"));
        assert!(result.line_required);
        assert!(promotion_allowed(&result));

        let player = resolve_provider_market(&contract, "the_odds_api", "player_shots_on_target");
        assert_eq!(player.status, MarketResolutionStatus::Resolved);
        assert!(player.player_required);
        assert!(player.lineup_required);
        assert!(promotion_allowed(&player));
    }

    #[test]
    fn rejects_unknown_market_for_review() {
        let contract = parse_market_registry_contract(include_str!("../../configs/market_registry.v237.json"))
            .expect("parse registry");
        let result = resolve_provider_market(&contract, "the_odds_api", "special_combo_unknown");
        assert_eq!(result.status, MarketResolutionStatus::NeedsReview);
        assert!(!promotion_allowed(&result));
        assert!(result.review_required);
        assert_eq!(result.reason.as_deref(), Some("unmapped_provider_market"));
    }

    #[test]
    fn checks_bronze_market_discovery_rows() {
        let contract = parse_market_registry_contract(include_str!("../../configs/market_registry.v237.json"))
            .expect("parse registry");
        let parsed = parse_the_odds_api_event_markets_sample(
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            "2026-06-16T18:02:00Z",
        )
        .expect("parse provider sample");
        let resolutions = resolve_market_discovery_rows(&contract, &parsed.markets);
        assert_eq!(resolutions.len(), 8);
        assert_eq!(resolutions.iter().filter(|row| promotion_allowed(row)).count(), 7);
        assert_eq!(resolutions.iter().filter(|row| row.review_required).count(), 1);
    }
}
