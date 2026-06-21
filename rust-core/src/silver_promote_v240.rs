use crate::{
    build_identity_preview_from_offline_samples, build_preview_from_offline_samples,
    IdentityMappingPreview, SilverMarketMappingPreview,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverPromotionPreview {
    pub schema: String,
    pub preview_id: String,
    pub created_at: String,
    pub preview_only: bool,
    pub market_preview: SilverMarketMappingPreview,
    pub identity_preview: IdentityMappingPreview,
    pub silver_ready: bool,
    pub promoted_fact_bundles: Vec<SilverFactBundlePreview>,
    pub blocked_fact_bundles: Vec<SilverBlockedBundle>,
    pub market_review_count: usize,
    pub identity_review_count: usize,
    pub blocked_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverFactBundlePreview {
    pub bundle_id: String,
    pub bundle_kind: String,
    pub status: String,
    pub reason: String,
    pub fixture_refs: usize,
    pub team_refs: usize,
    pub player_refs: usize,
    pub resolved_market_groups: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverBlockedBundle {
    pub bundle_id: String,
    pub bundle_kind: String,
    pub reason: String,
    pub blocked_rows: usize,
    pub promotion_allowed: bool,
}

pub fn build_silver_promotion_preview(
    market_preview: SilverMarketMappingPreview,
    identity_preview: IdentityMappingPreview,
    preview_id: &str,
    created_at: &str,
) -> SilverPromotionPreview {
    let market_review_count = market_preview.review_count;
    let identity_review_count = identity_preview.review_count;
    let mut promoted_fact_bundles = Vec::new();
    let mut blocked_fact_bundles = Vec::new();

    if market_review_count == 0 && identity_review_count == 0 {
        promoted_fact_bundles.push(SilverFactBundlePreview {
            bundle_id: "silver_market_identity_bundle".to_string(),
            bundle_kind: "market_identity_fact_preview".to_string(),
            status: "preview_ready".to_string(),
            reason: "markets_and_identities_resolved".to_string(),
            fixture_refs: identity_preview.fixture_refs,
            team_refs: identity_preview.team_refs,
            player_refs: identity_preview.player_refs,
            resolved_market_groups: market_preview.resolved_count,
        });
    } else {
        if market_review_count > 0 {
            blocked_fact_bundles.push(SilverBlockedBundle {
                bundle_id: "blocked_market_mapping".to_string(),
                bundle_kind: "market_mapping".to_string(),
                reason: "unresolved_market_mappings".to_string(),
                blocked_rows: market_review_count,
                promotion_allowed: false,
            });
        }
        if identity_review_count > 0 {
            blocked_fact_bundles.push(SilverBlockedBundle {
                bundle_id: "blocked_identity_mapping".to_string(),
                bundle_kind: "identity_mapping".to_string(),
                reason: "unresolved_identity_mappings".to_string(),
                blocked_rows: identity_review_count,
                promotion_allowed: false,
            });
        }
    }

    SilverPromotionPreview {
        schema: "omnibet.silver_promotion_preview.v240".to_string(),
        preview_id: preview_id.to_string(),
        created_at: created_at.to_string(),
        preview_only: true,
        silver_ready: promoted_fact_bundles.len() == 1 && blocked_fact_bundles.is_empty(),
        market_preview,
        identity_preview,
        promoted_fact_bundles,
        blocked_count: blocked_fact_bundles.len(),
        blocked_fact_bundles,
        market_review_count,
        identity_review_count,
    }
}

pub fn build_silver_promotion_preview_from_offline_samples(
    market_registry_text: &str,
    identity_contract_text: &str,
    odds_sample_text: &str,
    football_sample_text: &str,
    created_at: &str,
) -> Result<SilverPromotionPreview, String> {
    let market_preview = build_preview_from_offline_samples(
        market_registry_text,
        odds_sample_text,
        created_at,
    )?;
    let identity_preview = build_identity_preview_from_offline_samples(
        identity_contract_text,
        odds_sample_text,
        football_sample_text,
        created_at,
    )?;
    Ok(build_silver_promotion_preview(
        market_preview,
        identity_preview,
        "v240_offline_silver_promotion_preview",
        created_at,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blocks_silver_preview_when_market_review_exists() {
        let preview = build_silver_promotion_preview_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build silver promotion preview");
        assert_eq!(preview.schema, "omnibet.silver_promotion_preview.v240");
        assert!(preview.preview_only);
        assert!(!preview.silver_ready);
        assert_eq!(preview.market_review_count, 1);
        assert_eq!(preview.identity_review_count, 0);
        assert_eq!(preview.blocked_count, 1);
        assert!(preview.promoted_fact_bundles.is_empty());
        assert!(preview.blocked_fact_bundles.iter().any(|row| row.reason == "unresolved_market_mappings" && !row.promotion_allowed));
        assert!(preview.market_preview.review_rows.iter().any(|row| row.provider_market_key == "special_combo_unknown"));
        assert_eq!(preview.identity_preview.resolved_count, 15);
    }
}
