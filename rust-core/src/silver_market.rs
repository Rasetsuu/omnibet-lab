use crate::market_registry::{
    parse_market_registry_contract, promotion_allowed, resolve_market_discovery_rows,
    MarketRegistryContract, MarketResolution, MarketResolutionStatus,
};
use crate::provider::{parse_the_odds_api_event_markets_sample, ProviderMarketDiscoverySnapshot};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverMarketMappingPreview {
    pub schema: String,
    pub preview_id: String,
    pub created_at: String,
    pub source: String,
    pub resolved_rows: Vec<SilverMarketMappingRow>,
    pub review_rows: Vec<SilverMarketReviewRow>,
    pub total_market_rows: usize,
    pub resolved_count: usize,
    pub review_count: usize,
    pub promotion_blocked_count: usize,
    pub automatic_unknown_promotion_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverMarketMappingRow {
    pub provider_id: String,
    pub provider_market_key: String,
    pub canonical_market_id: String,
    pub family: String,
    pub settlement_rule: String,
    pub line_required: bool,
    pub player_required: bool,
    pub lineup_required: bool,
    pub source_event_id_count: usize,
    pub bookmaker_count: usize,
    pub outcome_rows: usize,
    pub promoted_to_silver_preview: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverMarketReviewRow {
    pub provider_id: String,
    pub provider_market_key: String,
    pub reason: String,
    pub source_event_id_count: usize,
    pub bookmaker_count: usize,
    pub outcome_rows: usize,
    pub promotion_allowed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct MarketGroupKey {
    provider_id: String,
    provider_market_key: String,
}

#[derive(Debug, Default, Clone)]
struct MarketGroupStats {
    source_event_ids: std::collections::BTreeSet<String>,
    bookmakers: std::collections::BTreeSet<String>,
    outcome_rows: usize,
}

pub fn build_silver_market_mapping_preview(
    registry: &MarketRegistryContract,
    market_rows: &[ProviderMarketDiscoverySnapshot],
    preview_id: &str,
    created_at: &str,
) -> SilverMarketMappingPreview {
    let resolutions = resolve_market_discovery_rows(registry, market_rows);
    let mut groups: BTreeMap<MarketGroupKey, MarketGroupStats> = BTreeMap::new();
    for row in market_rows {
        let key = MarketGroupKey {
            provider_id: row.source_id.clone(),
            provider_market_key: row.market_key.clone(),
        };
        let entry = groups.entry(key).or_default();
        entry.source_event_ids.insert(row.source_event_id.clone());
        entry.bookmakers.insert(row.bookmaker_key.clone());
        entry.outcome_rows += row.outcome_count;
    }

    let mut resolution_by_key = BTreeMap::new();
    for resolution in resolutions {
        resolution_by_key.insert(
            MarketGroupKey {
                provider_id: resolution.provider_id.clone(),
                provider_market_key: resolution.provider_market_key.clone(),
            },
            resolution,
        );
    }

    let mut resolved_rows = Vec::new();
    let mut review_rows = Vec::new();
    for (key, stats) in groups {
        let resolution = resolution_by_key.get(&key).cloned().unwrap_or_else(|| MarketResolution {
            provider_id: key.provider_id.clone(),
            provider_market_key: key.provider_market_key.clone(),
            status: MarketResolutionStatus::NeedsReview,
            canonical_market_id: None,
            family: None,
            settlement_rule: None,
            line_required: false,
            player_required: false,
            lineup_required: false,
            review_required: true,
            reason: Some("missing_resolution".to_string()),
        });
        if promotion_allowed(&resolution) {
            resolved_rows.push(SilverMarketMappingRow {
                provider_id: key.provider_id,
                provider_market_key: key.provider_market_key,
                canonical_market_id: resolution.canonical_market_id.unwrap_or_default(),
                family: resolution.family.unwrap_or_default(),
                settlement_rule: resolution.settlement_rule.unwrap_or_default(),
                line_required: resolution.line_required,
                player_required: resolution.player_required,
                lineup_required: resolution.lineup_required,
                source_event_id_count: stats.source_event_ids.len(),
                bookmaker_count: stats.bookmakers.len(),
                outcome_rows: stats.outcome_rows,
                promoted_to_silver_preview: true,
            });
        } else {
            review_rows.push(SilverMarketReviewRow {
                provider_id: key.provider_id,
                provider_market_key: key.provider_market_key,
                reason: resolution.reason.unwrap_or_else(|| "review_required".to_string()),
                source_event_id_count: stats.source_event_ids.len(),
                bookmaker_count: stats.bookmakers.len(),
                outcome_rows: stats.outcome_rows,
                promotion_allowed: false,
            });
        }
    }
    let total_market_rows = market_rows.len();
    let resolved_count = resolved_rows.len();
    let review_count = review_rows.len();
    SilverMarketMappingPreview {
        schema: "omnibet.silver_market_mapping_preview.v238".to_string(),
        preview_id: preview_id.to_string(),
        created_at: created_at.to_string(),
        source: "bronze_market_discovery".to_string(),
        resolved_rows,
        review_rows,
        total_market_rows,
        resolved_count,
        review_count,
        promotion_blocked_count: review_count,
        automatic_unknown_promotion_allowed: false,
    }
}

pub fn build_preview_from_offline_samples(
    registry_text: &str,
    odds_sample_text: &str,
    created_at: &str,
) -> Result<SilverMarketMappingPreview, String> {
    let registry = parse_market_registry_contract(registry_text)
        .map_err(|e| format!("parse market registry: {}", e))?;
    let parsed = parse_the_odds_api_event_markets_sample(odds_sample_text, created_at)?;
    Ok(build_silver_market_mapping_preview(
        &registry,
        &parsed.markets,
        "v238_offline_market_mapping_preview",
        created_at,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_silver_mapping_preview_without_promoting_unknowns() {
        let preview = build_preview_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build preview");
        assert_eq!(preview.schema, "omnibet.silver_market_mapping_preview.v238");
        assert_eq!(preview.total_market_rows, 8);
        assert_eq!(preview.resolved_count, 6);
        assert_eq!(preview.review_count, 1);
        assert_eq!(preview.promotion_blocked_count, 1);
        assert!(!preview.automatic_unknown_promotion_allowed);
        assert!(preview.resolved_rows.iter().any(|row| row.canonical_market_id == "player_shots_on_target" && row.lineup_required));
        assert!(preview.review_rows.iter().any(|row| row.provider_market_key == "special_combo_unknown" && !row.promotion_allowed));
    }
}
