use crate::{
    build_patched_silver_preview_from_offline_samples, ReviewQueueReport, SilverPromotionPreview,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverFactPreviewBundle {
    pub schema: String,
    pub bundle_id: String,
    pub created_at: String,
    pub source_preview_id: String,
    pub preview_only: bool,
    pub training_dataset_promotion_allowed: bool,
    pub silver_ready_input: bool,
    pub review_rows_at_build_time: usize,
    pub market_fact_rows: usize,
    pub identity_link_rows: usize,
    pub total_rows: usize,
    pub rows: Vec<SilverFactPreviewRow>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverFactPreviewRow {
    pub row_id: String,
    pub fact_kind: String,
    pub provider_id: String,
    pub provider_key: String,
    pub canonical_id: String,
    pub source_relation: String,
    pub preview_only: bool,
    pub training_dataset_promotion_allowed: bool,
}

pub fn build_silver_fact_preview_bundle(
    preview: &SilverPromotionPreview,
    review: &ReviewQueueReport,
    bundle_id: &str,
    created_at: &str,
) -> Result<SilverFactPreviewBundle, String> {
    if !preview.silver_ready {
        return Err("silver fact preview requires silver_ready input".to_string());
    }
    if review.total_review_rows != 0 {
        return Err("silver fact preview requires clean review queue".to_string());
    }

    let mut rows = Vec::new();
    for market in &preview.market_preview.resolved_rows {
        rows.push(SilverFactPreviewRow {
            row_id: format!("market:{}:{}", market.provider_id, market.provider_market_key),
            fact_kind: "market_mapping_fact_preview".to_string(),
            provider_id: market.provider_id.clone(),
            provider_key: market.provider_market_key.clone(),
            canonical_id: market.canonical_market_id.clone(),
            source_relation: format!("{}:{}", market.family, market.settlement_rule),
            preview_only: true,
            training_dataset_promotion_allowed: false,
        });
    }
    for identity in &preview.identity_preview.resolved_rows {
        rows.push(SilverFactPreviewRow {
            row_id: format!(
                "identity:{:?}:{}:{}",
                identity.entity_kind,
                identity.provider_id,
                identity.provider_entity_id.clone().unwrap_or_else(|| identity.display_name.clone())
            ),
            fact_kind: "identity_link_fact_preview".to_string(),
            provider_id: identity.provider_id.clone(),
            provider_key: identity.provider_entity_id.clone().unwrap_or_else(|| identity.display_name.clone()),
            canonical_id: identity.canonical_id.clone().unwrap_or_default(),
            source_relation: format!("{:?}", identity.entity_kind),
            preview_only: true,
            training_dataset_promotion_allowed: false,
        });
    }

    let market_fact_rows = preview.market_preview.resolved_rows.len();
    let identity_link_rows = preview.identity_preview.resolved_rows.len();
    let total_rows = rows.len();
    Ok(SilverFactPreviewBundle {
        schema: "omnibet.silver_fact_preview_bundle.v243".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        source_preview_id: preview.preview_id.clone(),
        preview_only: true,
        training_dataset_promotion_allowed: false,
        silver_ready_input: preview.silver_ready,
        review_rows_at_build_time: review.total_review_rows,
        market_fact_rows,
        identity_link_rows,
        total_rows,
        rows,
    })
}

pub fn build_silver_fact_preview_bundle_from_offline_samples(
    registry_text: &str,
    patch_text: &str,
    identity_contract_text: &str,
    odds_sample_text: &str,
    football_sample_text: &str,
    created_at: &str,
) -> Result<SilverFactPreviewBundle, String> {
    let (preview, review) = build_patched_silver_preview_from_offline_samples(
        registry_text,
        patch_text,
        identity_contract_text,
        odds_sample_text,
        football_sample_text,
        created_at,
    )?;
    build_silver_fact_preview_bundle(
        &preview,
        &review,
        "v243_offline_silver_fact_preview_bundle",
        created_at,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::build_silver_promotion_preview_from_offline_samples;
    use crate::build_review_queue_report;

    #[test]
    fn builds_preview_bundle_after_clean_review_queue() {
        let bundle = build_silver_fact_preview_bundle_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/market_review_patch.v242.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build silver fact preview bundle");
        assert_eq!(bundle.schema, "omnibet.silver_fact_preview_bundle.v243");
        assert!(bundle.preview_only);
        assert!(!bundle.training_dataset_promotion_allowed);
        assert_eq!(bundle.review_rows_at_build_time, 0);
        assert_eq!(bundle.market_fact_rows, 7);
        assert_eq!(bundle.identity_link_rows, 15);
        assert_eq!(bundle.total_rows, 22);
        assert!(bundle.rows.iter().any(|row| row.provider_key == "special_combo_unknown" && row.canonical_id == "sample_same_game_combo_france_win_player_shot_team_corners"));
    }

    #[test]
    fn refuses_bundle_when_review_queue_is_not_clean() {
        let preview = build_silver_promotion_preview_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build blocked preview");
        let review = build_review_queue_report(&preview, "blocked_review_queue", "2026-06-20T00:00:00Z");
        let result = build_silver_fact_preview_bundle(
            &preview,
            &review,
            "should_not_build",
            "2026-06-20T00:00:00Z",
        );
        assert!(result.is_err());
    }
}
