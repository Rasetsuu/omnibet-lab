use crate::{BronzePreviewFieldSchemaBundle, BronzePreviewFieldSchemaRow};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeValidationBatchReport {
    pub schema: String,
    pub batch_id: String,
    pub created_at: String,
    pub source_bundle_id: String,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
    pub value_validation: BronzePreviewValueValidationBundle,
    pub review_reasons: BronzePreviewReviewReasonBundle,
    pub readiness: BronzeCandidateReadinessSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewValueValidationBundle {
    pub schema: String,
    pub bundle_id: String,
    pub source_bundle_id: String,
    pub quarantine_only: bool,
    pub total_rows: u64,
    pub value_ok_rows: u64,
    pub review_required_rows: u64,
    pub rows: Vec<BronzePreviewValueValidationRow>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewValueValidationRow {
    pub row_id: String,
    pub row_class: String,
    pub value_status: String,
    pub review_reasons: Vec<String>,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewReviewReasonBundle {
    pub schema: String,
    pub bundle_id: String,
    pub total_review_rows: u64,
    pub reason_counts: BTreeMap<String, u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeCandidateReadinessSummary {
    pub schema: String,
    pub bundle_id: String,
    pub ready_for_bronze_write: bool,
    pub ready_for_silver_promotion: bool,
    pub ready_for_evaluation: bool,
    pub ready_for_training: bool,
    pub paper_only: bool,
    pub total_rows: u64,
    pub value_ok_rows: u64,
    pub blocked_rows: u64,
    pub blocker_summary: Vec<String>,
}

pub fn build_bronze_validation_batch_report(
    source: &BronzePreviewFieldSchemaBundle,
    field_values_by_row_id: &BTreeMap<String, BTreeMap<String, String>>,
    batch_id: &str,
    created_at: &str,
) -> BronzeValidationBatchReport {
    let value_validation = validate_bronze_preview_values(
        source,
        field_values_by_row_id,
        &format!("{}::value_validation", batch_id),
    );
    let review_reasons = summarize_bronze_preview_review_reasons(
        &value_validation,
        &format!("{}::review_reasons", batch_id),
    );
    let readiness = summarize_bronze_candidate_readiness(
        &value_validation,
        &review_reasons,
        &format!("{}::readiness", batch_id),
    );
    BronzeValidationBatchReport {
        schema: "omnibet.bronze_validation_batch_report.v252".to_string(),
        batch_id: batch_id.to_string(),
        created_at: created_at.to_string(),
        source_bundle_id: source.bundle_id.clone(),
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
        value_validation,
        review_reasons,
        readiness,
    }
}

pub fn validate_bronze_preview_values(
    source: &BronzePreviewFieldSchemaBundle,
    field_values_by_row_id: &BTreeMap<String, BTreeMap<String, String>>,
    bundle_id: &str,
) -> BronzePreviewValueValidationBundle {
    let mut rows = Vec::new();
    let mut value_ok_rows = 0u64;
    let mut review_required_rows = 0u64;
    for row in &source.rows {
        let values = field_values_by_row_id.get(&row.row_id);
        let validated = validate_bronze_preview_value_row(row, values);
        if validated.value_status == "value_ok" {
            value_ok_rows += 1;
        } else {
            review_required_rows += 1;
        }
        rows.push(validated);
    }
    BronzePreviewValueValidationBundle {
        schema: "omnibet.bronze_preview_value_validation_bundle.v252".to_string(),
        bundle_id: bundle_id.to_string(),
        source_bundle_id: source.bundle_id.clone(),
        quarantine_only: true,
        total_rows: rows.len() as u64,
        value_ok_rows,
        review_required_rows,
        rows,
    }
}

pub fn validate_bronze_preview_value_row(
    row: &BronzePreviewFieldSchemaRow,
    values: Option<&BTreeMap<String, String>>,
) -> BronzePreviewValueValidationRow {
    let mut review_reasons = Vec::new();
    if row.schema_status != "schema_ok" {
        review_reasons.push("schema_not_ok".to_string());
        if !row.missing_fields.is_empty() {
            review_reasons.push(format!("missing_fields:{}", row.missing_fields.join(",")));
        }
        if let Some(reason) = &row.review_reason {
            review_reasons.push(format!("schema_review:{}", normalize_reason(reason)));
        }
    }

    let Some(values) = values else {
        review_reasons.push("missing_value_payload".to_string());
        return value_row(row, review_reasons);
    };

    match row.row_class.as_str() {
        "fixture_result" => validate_fixture_result_values(values, &mut review_reasons),
        "odds_snapshot" => validate_odds_snapshot_values(values, &mut review_reasons),
        "lineup_event_context" => validate_lineup_event_context_values(values, &mut review_reasons),
        other => review_reasons.push(format!("unsupported_row_class:{}", other)),
    }
    value_row(row, review_reasons)
}

fn value_row(row: &BronzePreviewFieldSchemaRow, mut review_reasons: Vec<String>) -> BronzePreviewValueValidationRow {
    review_reasons.sort();
    review_reasons.dedup();
    BronzePreviewValueValidationRow {
        row_id: row.row_id.clone(),
        row_class: row.row_class.clone(),
        value_status: if review_reasons.is_empty() { "value_ok" } else { "review_required" }.to_string(),
        review_reasons,
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
    }
}

fn validate_fixture_result_values(values: &BTreeMap<String, String>, review_reasons: &mut Vec<String>) {
    require_non_empty(values, "fixture_id", review_reasons);
    require_non_empty(values, "home_team", review_reasons);
    require_non_empty(values, "away_team", review_reasons);
    require_timestamp_shape(values, "kickoff_utc", review_reasons);
    require_non_empty(values, "result_status", review_reasons);
}

fn validate_odds_snapshot_values(values: &BTreeMap<String, String>, review_reasons: &mut Vec<String>) {
    require_non_empty(values, "fixture_id", review_reasons);
    require_non_empty(values, "provider_id", review_reasons);
    require_non_empty(values, "bookmaker_id", review_reasons);
    require_non_empty(values, "market_key", review_reasons);
    require_non_empty(values, "selection_key", review_reasons);
    require_decimal_price(values, "price_decimal", review_reasons);
    require_timestamp_shape(values, "snapshot_utc", review_reasons);
}

fn validate_lineup_event_context_values(values: &BTreeMap<String, String>, review_reasons: &mut Vec<String>) {
    require_non_empty(values, "fixture_id", review_reasons);
    require_non_empty(values, "provider_id", review_reasons);
    require_non_empty(values, "entity_id", review_reasons);
    require_non_empty(values, "event_type", review_reasons);
    require_timestamp_shape(values, "observed_at_utc", review_reasons);
}

fn require_non_empty(values: &BTreeMap<String, String>, field: &str, review_reasons: &mut Vec<String>) {
    if values.get(field).map(|value| value.trim().is_empty()).unwrap_or(true) {
        review_reasons.push(format!("empty_or_missing:{}", field));
    }
}

fn require_decimal_price(values: &BTreeMap<String, String>, field: &str, review_reasons: &mut Vec<String>) {
    match values.get(field).map(|value| value.trim().parse::<f64>()) {
        Some(Ok(value)) if value > 1.0 && value < 1000.0 => {}
        _ => review_reasons.push(format!("invalid_decimal_price:{}", field)),
    }
}

fn require_timestamp_shape(values: &BTreeMap<String, String>, field: &str, review_reasons: &mut Vec<String>) {
    match values.get(field).map(|value| value.trim()) {
        Some(value) if looks_like_utc_timestamp(value) => {}
        _ => review_reasons.push(format!("invalid_timestamp_shape:{}", field)),
    }
}

fn looks_like_utc_timestamp(value: &str) -> bool {
    value.len() >= 20 && value.contains('T') && value.ends_with('Z')
}

fn normalize_reason(value: &str) -> String {
    value
        .chars()
        .map(|ch| if ch.is_ascii_alphanumeric() { ch.to_ascii_lowercase() } else { '_' })
        .collect::<String>()
        .split('_')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

pub fn summarize_bronze_preview_review_reasons(
    validation: &BronzePreviewValueValidationBundle,
    bundle_id: &str,
) -> BronzePreviewReviewReasonBundle {
    let mut reason_counts = BTreeMap::new();
    let mut total_review_rows = 0u64;
    for row in &validation.rows {
        if row.value_status != "value_ok" {
            total_review_rows += 1;
        }
        for reason in &row.review_reasons {
            *reason_counts.entry(reason.clone()).or_insert(0) += 1;
        }
    }
    BronzePreviewReviewReasonBundle {
        schema: "omnibet.bronze_preview_review_reason_bundle.v252".to_string(),
        bundle_id: bundle_id.to_string(),
        total_review_rows,
        reason_counts,
    }
}

pub fn summarize_bronze_candidate_readiness(
    validation: &BronzePreviewValueValidationBundle,
    reasons: &BronzePreviewReviewReasonBundle,
    bundle_id: &str,
) -> BronzeCandidateReadinessSummary {
    let mut blocker_summary = Vec::new();
    if validation.review_required_rows > 0 {
        blocker_summary.push(format!("review_required_rows:{}", validation.review_required_rows));
    }
    for (reason, count) in &reasons.reason_counts {
        blocker_summary.push(format!("{}:{}", reason, count));
    }
    BronzeCandidateReadinessSummary {
        schema: "omnibet.bronze_candidate_readiness_summary.v252".to_string(),
        bundle_id: bundle_id.to_string(),
        ready_for_bronze_write: false,
        ready_for_silver_promotion: false,
        ready_for_evaluation: false,
        ready_for_training: false,
        paper_only: true,
        total_rows: validation.total_rows,
        value_ok_rows: validation.value_ok_rows,
        blocked_rows: validation.review_required_rows,
        blocker_summary,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn field_schema_row(row_id: &str, row_class: &str, schema_status: &str) -> BronzePreviewFieldSchemaRow {
        BronzePreviewFieldSchemaRow {
            row_id: row_id.to_string(),
            row_class: row_class.to_string(),
            schema_status: schema_status.to_string(),
            required_fields: Vec::new(),
            present_fields: Vec::new(),
            missing_fields: Vec::new(),
            review_reason: None,
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
        }
    }

    fn field_schema_bundle() -> BronzePreviewFieldSchemaBundle {
        BronzePreviewFieldSchemaBundle {
            schema: "omnibet.bronze_preview_field_schema_bundle.v251".to_string(),
            bundle_id: "v251_test_bundle".to_string(),
            created_at: "2026-06-21T00:00:00Z".to_string(),
            source_bundle_id: "v250_test_bundle".to_string(),
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
            total_rows: 3,
            schema_ok_rows: 2,
            review_required_rows: 1,
            rows: vec![
                field_schema_row("odds_ok", "odds_snapshot", "schema_ok"),
                field_schema_row("odds_bad", "odds_snapshot", "schema_ok"),
                field_schema_row("fixture_review", "fixture_result", "review_required"),
            ],
        }
    }

    fn values(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs.iter().map(|(key, value)| ((*key).to_string(), (*value).to_string())).collect()
    }

    #[test]
    fn batch_validates_values_summarizes_reasons_and_blocks_readiness() {
        let mut payloads = BTreeMap::new();
        payloads.insert(
            "odds_ok".to_string(),
            values(&[
                ("fixture_id", "fixture-1"),
                ("provider_id", "provider-a"),
                ("bookmaker_id", "book-a"),
                ("market_key", "1x2"),
                ("selection_key", "home"),
                ("price_decimal", "2.10"),
                ("snapshot_utc", "2026-06-01T12:00:00Z"),
            ]),
        );
        payloads.insert(
            "odds_bad".to_string(),
            values(&[
                ("fixture_id", "fixture-2"),
                ("provider_id", "provider-a"),
                ("bookmaker_id", ""),
                ("market_key", "1x2"),
                ("selection_key", "away"),
                ("price_decimal", "nope"),
                ("snapshot_utc", "not-a-time"),
            ]),
        );
        let report = build_bronze_validation_batch_report(
            &field_schema_bundle(),
            &payloads,
            "v252_test_batch",
            "2026-06-21T00:00:00Z",
        );
        assert_eq!(report.schema, "omnibet.bronze_validation_batch_report.v252");
        assert_eq!(report.value_validation.total_rows, 3);
        assert_eq!(report.value_validation.value_ok_rows, 1);
        assert_eq!(report.value_validation.review_required_rows, 2);
        assert!(report.review_reasons.reason_counts.contains_key("invalid_decimal_price:price_decimal"));
        assert!(report.review_reasons.reason_counts.contains_key("invalid_timestamp_shape:snapshot_utc"));
        assert!(!report.readiness.ready_for_bronze_write);
        assert!(!report.readiness.ready_for_evaluation);
        assert!(!report.readiness.ready_for_training);
        assert!(report.quarantine_only);
        assert!(!report.training_dataset_promotion_allowed);
    }

    #[test]
    fn value_rows_keep_all_safety_flags_locked() {
        let report = build_bronze_validation_batch_report(
            &field_schema_bundle(),
            &BTreeMap::new(),
            "v252_test_batch",
            "2026-06-21T00:00:00Z",
        );
        assert!(report.value_validation.rows.iter().all(|row| row.quarantine_only));
        assert!(report.value_validation.rows.iter().all(|row| !row.import_allowed_now));
        assert!(report.value_validation.rows.iter().all(|row| !row.promotion_allowed));
        assert!(report.value_validation.rows.iter().all(|row| !row.evaluation_allowed));
        assert!(report.value_validation.rows.iter().all(|row| !row.training_dataset_promotion_allowed));
    }
}
