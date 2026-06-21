use crate::{
    build_silver_promotion_preview_from_offline_samples, SilverPromotionPreview,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReviewQueueReport {
    pub schema: String,
    pub report_id: String,
    pub created_at: String,
    pub source_preview_id: String,
    pub review_required: bool,
    pub market_review_rows: Vec<ReviewQueueRow>,
    pub identity_review_rows: Vec<ReviewQueueRow>,
    pub total_review_rows: usize,
    pub auto_approval_allowed: bool,
    pub silver_ready_after_review: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReviewQueueRow {
    pub review_id: String,
    pub review_kind: String,
    pub provider_id: String,
    pub provider_key: String,
    pub reason: String,
    pub suggested_action: String,
    pub required_fields: Vec<String>,
    pub promotion_allowed_before_review: bool,
}

pub fn build_review_queue_report(
    preview: &SilverPromotionPreview,
    report_id: &str,
    created_at: &str,
) -> ReviewQueueReport {
    let mut market_review_rows = Vec::new();
    for row in &preview.market_preview.review_rows {
        market_review_rows.push(ReviewQueueRow {
            review_id: format!("market:{}:{}", row.provider_id, row.provider_market_key),
            review_kind: "market_mapping".to_string(),
            provider_id: row.provider_id.clone(),
            provider_key: row.provider_market_key.clone(),
            reason: row.reason.clone(),
            suggested_action: "add_canonical_market_alias_and_settlement_rule_or_keep_blocked".to_string(),
            required_fields: vec![
                "canonical_market_id".to_string(),
                "market_family".to_string(),
                "settlement_rule".to_string(),
                "selection_scope".to_string(),
                "line_required".to_string(),
                "player_required".to_string(),
                "lineup_required".to_string(),
                "correlation_group".to_string(),
            ],
            promotion_allowed_before_review: false,
        });
    }

    let mut identity_review_rows = Vec::new();
    for row in &preview.identity_preview.review_rows {
        identity_review_rows.push(ReviewQueueRow {
            review_id: format!(
                "identity:{:?}:{}:{}",
                row.entity_kind,
                row.provider_id,
                row.provider_entity_id.clone().unwrap_or_else(|| row.display_name.clone())
            ),
            review_kind: "identity_mapping".to_string(),
            provider_id: row.provider_id.clone(),
            provider_key: row.provider_entity_id.clone().unwrap_or_else(|| row.display_name.clone()),
            reason: row.reason.clone().unwrap_or_else(|| "unmapped_provider_identity".to_string()),
            suggested_action: "add_provider_identity_alias_or_keep_blocked".to_string(),
            required_fields: vec![
                "canonical_id".to_string(),
                "entity_kind".to_string(),
                "display_name".to_string(),
                "provider_entity_id_or_name".to_string(),
            ],
            promotion_allowed_before_review: false,
        });
    }

    let total_review_rows = market_review_rows.len() + identity_review_rows.len();
    ReviewQueueReport {
        schema: "omnibet.review_queue_report.v241".to_string(),
        report_id: report_id.to_string(),
        created_at: created_at.to_string(),
        source_preview_id: preview.preview_id.clone(),
        review_required: total_review_rows > 0,
        market_review_rows,
        identity_review_rows,
        total_review_rows,
        auto_approval_allowed: false,
        silver_ready_after_review: total_review_rows == 0,
    }
}

pub fn build_review_queue_report_from_offline_samples(
    market_registry_text: &str,
    identity_contract_text: &str,
    odds_sample_text: &str,
    football_sample_text: &str,
    created_at: &str,
) -> Result<ReviewQueueReport, String> {
    let preview = build_silver_promotion_preview_from_offline_samples(
        market_registry_text,
        identity_contract_text,
        odds_sample_text,
        football_sample_text,
        created_at,
    )?;
    Ok(build_review_queue_report(
        &preview,
        "v241_offline_review_queue_report",
        created_at,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_review_queue_for_unresolved_market() {
        let report = build_review_queue_report_from_offline_samples(
            include_str!("../../configs/market_registry.v237.json"),
            include_str!("../../configs/identity_mapping_preview.v239.json"),
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-20T00:00:00Z",
        )
        .expect("build review queue");
        assert_eq!(report.schema, "omnibet.review_queue_report.v241");
        assert!(report.review_required);
        assert_eq!(report.total_review_rows, 1);
        assert_eq!(report.market_review_rows.len(), 1);
        assert_eq!(report.identity_review_rows.len(), 0);
        assert!(!report.auto_approval_allowed);
        assert!(!report.silver_ready_after_review);
        let row = &report.market_review_rows[0];
        assert_eq!(row.provider_key, "special_combo_unknown");
        assert_eq!(row.review_kind, "market_mapping");
        assert!(!row.promotion_allowed_before_review);
        assert!(row.required_fields.iter().any(|field| field == "settlement_rule"));
    }
}
