use crate::{
    build_review_queue_report, build_silver_promotion_preview,
    build_silver_promotion_preview_from_offline_samples, build_preview_from_offline_samples,
    build_identity_preview_from_offline_samples, parse_market_registry_contract,
    CanonicalMarket, MarketRegistryContract, ProviderMarketAlias, ReviewQueueReport,
    SilverPromotionPreview,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketReviewPatchContract {
    pub schema: String,
    pub goal: String,
    pub scope: String,
    pub automatic_application_allowed: bool,
    pub production_use_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
    pub review_record: MarketReviewRecord,
    pub canonical_markets_to_add: Vec<CanonicalMarket>,
    pub provider_aliases_to_add: Vec<ProviderMarketAlias>,
    pub expected_after_patch: ExpectedAfterPatch,
    pub safety_requirements: PatchSafetyRequirements,
    pub acceptance: PatchAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MarketReviewRecord {
    pub review_id: String,
    pub reviewed_by: String,
    pub reviewed_at: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ExpectedAfterPatch {
    pub market_review_count: usize,
    pub identity_review_count: usize,
    pub total_review_rows: usize,
    pub silver_ready: bool,
    pub resolved_market_groups: usize,
    pub review_market_groups: usize,
    pub blocked_promotions: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PatchSafetyRequirements {
    pub canonical_market_id_required: bool,
    pub family_required: bool,
    pub settlement_rule_required: bool,
    pub selection_scope_required: bool,
    pub correlation_group_required: bool,
    pub automatic_application_forbidden: bool,
    pub production_use_forbidden: bool,
    pub training_promotion_forbidden: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PatchAcceptance {
    pub rust_patch_application_added: bool,
    pub sample_unmapped_market_resolves_after_patch: bool,
    pub review_queue_clears_after_patch: bool,
    pub silver_ready_after_patch: bool,
    pub automatic_application_still_forbidden: bool,
    pub python_smoke_added: bool,
    pub ci_workflow_added: bool,
}

pub fn parse_market_review_patch(text: &str) -> Result<MarketReviewPatchContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_market_review_patch(patch: &MarketReviewPatchContract) -> Result<(), String> {
    if patch.schema != "omnibet.market_review_patch.v242" {
        return Err(format!("unexpected market review patch schema: {}", patch.schema));
    }
    if patch.scope != "offline_sample_only" {
        return Err("v242 patch must remain offline-sample-only".to_string());
    }
    if patch.automatic_application_allowed || patch.production_use_allowed || patch.training_dataset_promotion_allowed {
        return Err("automatic, production, and training use must remain forbidden".to_string());
    }
    if patch.canonical_markets_to_add.is_empty() || patch.provider_aliases_to_add.is_empty() {
        return Err("patch must include canonical market and provider alias rows".to_string());
    }
    for market in &patch.canonical_markets_to_add {
        if market.canonical_market_id.trim().is_empty()
            || market.family.trim().is_empty()
            || market.settlement_rule.trim().is_empty()
            || market.selection_scope.trim().is_empty()
            || market.correlation_group.trim().is_empty()
        {
            return Err(format!("patch market missing required fields: {}", market.canonical_market_id));
        }
    }
    for alias in &patch.provider_aliases_to_add {
        if alias.review_required {
            return Err(format!("patched alias cannot still require review: {}", alias.provider_market_key));
        }
        if alias.provider_market_key != "special_combo_unknown" {
            return Err("v242 sample patch may only target special_combo_unknown".to_string());
        }
    }
    Ok(())
}

pub fn apply_market_review_patch(
    registry: &MarketRegistryContract,
    patch: &MarketReviewPatchContract,
) -> Result<MarketRegistryContract, String> {
    validate_market_review_patch(patch)?;
    let mut next = registry.clone();
    for market in &patch.canonical_markets_to_add {
        if !next.canonical_markets.iter().any(|row| row.canonical_market_id == market.canonical_market_id) {
            next.canonical_markets.push(market.clone());
        }
    }
    for alias in &patch.provider_aliases_to_add {
        if !next.provider_aliases.iter().any(|row| {
            row.provider_id == alias.provider_id && row.provider_market_key == alias.provider_market_key
        }) {
            next.provider_aliases.push(alias.clone());
        }
    }
    Ok(next)
}

pub fn build_patched_silver_preview_from_offline_samples(
    registry_text: &str,
    patch_text: &str,
    identity_contract_text: &str,
    odds_sample_text: &str,
    football_sample_text: &str,
    created_at: &str,
) -> Result<(SilverPromotionPreview, ReviewQueueReport), String> {
    let registry = parse_market_registry_contract(registry_text)
        .map_err(|e| format!("parse registry: {}", e))?;
    let patch = parse_market_review_patch(patch_text)
        .map_err(|e| format!("parse review patch: {}", e))?;
    let patched_registry = apply_market_review_patch(&registry, &patch)?;
    let patched_registry_text = serde_json::to_string(&patched_registry)
        .map_err(|e| format!("serialize patched registry: {}", e))?;
    let market_preview = build_preview_from_offline_samples(
        &patched_registry_text,
        odds_sample_text,
        created_at,
    )?;
    let identity_preview = build_identity_preview_from_offline_samples(
        identity_contract_text,
        odds_sample_text,
        football_sample_text,
        created_at,
    )?;
    let preview = build_silver_promotion_preview(
        market_preview,
        identity_preview,
        "v242_patched_silver_promotion_preview",
        created_at,
    );
    let review = build_review_queue_report(
        &preview,
        "v242_patched_review_queue_report",
        created_at,
    );
    Ok((preview, review))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn patch_clears_sample_review_queue_without_training_promotion() {
        let (preview, review) = build_patched_silver_preview_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/market_review_patch.v242.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build patched preview");
        assert!(preview.preview_only);
        assert!(preview.silver_ready);
        assert_eq!(preview.market_review_count, 0);
        assert_eq!(preview.identity_review_count, 0);
        assert_eq!(preview.market_preview.resolved_count, 7);
        assert_eq!(preview.market_preview.review_count, 0);
        assert_eq!(review.total_review_rows, 0);
        assert!(!review.auto_approval_allowed);
        assert!(review.silver_ready_after_review);
    }

    #[test]
    fn unpatched_preview_still_blocks_sample_market() {
        let preview = build_silver_promotion_preview_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build unpatched preview");
        assert!(!preview.silver_ready);
        assert_eq!(preview.market_review_count, 1);
    }
}
