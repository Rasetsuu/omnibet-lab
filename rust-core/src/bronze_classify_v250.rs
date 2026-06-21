use crate::{BronzeCandidatePreviewBundle, BronzeCandidatePreviewRow};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewClassificationBundle {
    pub schema: String,
    pub bundle_id: String,
    pub created_at: String,
    pub source_bundle_id: String,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
    pub total_rows: u64,
    pub classified_rows: u64,
    pub review_required_rows: u64,
    pub rows: Vec<BronzePreviewClassificationRow>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewClassificationRow {
    pub row_id: String,
    pub task_id: String,
    pub source_id: String,
    pub source_kind: String,
    pub row_class: String,
    pub classification_status: String,
    pub review_reason: Option<String>,
    pub raw_line_sha256: String,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
}

pub fn classify_bronze_candidate_preview_bundle(
    source: &BronzeCandidatePreviewBundle,
    bundle_id: &str,
    created_at: &str,
) -> BronzePreviewClassificationBundle {
    let mut rows = Vec::new();
    let mut classified_rows = 0u64;
    let mut review_required_rows = 0u64;

    for row in &source.rows {
        let classified = classify_bronze_candidate_preview_row(row);
        if classified.classification_status == "classified" {
            classified_rows += 1;
        } else {
            review_required_rows += 1;
        }
        rows.push(classified);
    }

    BronzePreviewClassificationBundle {
        schema: "omnibet.bronze_preview_classification_bundle.v250".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        source_bundle_id: source.bundle_id.clone(),
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
        total_rows: rows.len() as u64,
        classified_rows,
        review_required_rows,
        rows,
    }
}

pub fn classify_bronze_candidate_preview_row(
    row: &BronzeCandidatePreviewRow,
) -> BronzePreviewClassificationRow {
    let (row_class, status, review_reason) = match row.source_kind.as_str() {
        "fixtures_results" => ("fixture_result", "classified", None),
        "odds" => ("odds_snapshot", "classified", None),
        "lineups_events" => ("lineup_event_context", "classified", None),
        other => (
            "unknown",
            "review_required",
            Some(format!("unknown source kind: {}", other)),
        ),
    };
    BronzePreviewClassificationRow {
        row_id: row.row_id.clone(),
        task_id: row.task_id.clone(),
        source_id: row.source_id.clone(),
        source_kind: row.source_kind.clone(),
        row_class: row_class.to_string(),
        classification_status: status.to_string(),
        review_reason,
        raw_line_sha256: row.raw_line_sha256.clone(),
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn preview_row(row_id: &str, source_kind: &str) -> BronzeCandidatePreviewRow {
        BronzeCandidatePreviewRow {
            row_id: row_id.to_string(),
            task_id: format!("task_{}", row_id),
            source_id: format!("source_{}", row_id),
            source_kind: source_kind.to_string(),
            relative_path: format!("data/test/{}.jsonl", row_id),
            row_number: 1,
            raw_line_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_string(),
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
        }
    }

    fn preview_bundle() -> BronzeCandidatePreviewBundle {
        BronzeCandidatePreviewBundle {
            schema: "omnibet.bronze_candidate_preview_bundle.v249".to_string(),
            bundle_id: "v249_test_bundle".to_string(),
            created_at: "2026-06-21T00:00:00Z".to_string(),
            source_manifest_id: "manifest".to_string(),
            source_verification_schema: "omnibet.historical_source_verification_report.v248".to_string(),
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
            files_read: 1,
            total_rows: 4,
            rows: vec![
                preview_row("fixture", "fixtures_results"),
                preview_row("odds", "odds"),
                preview_row("events", "lineups_events"),
                preview_row("unknown", "provider_custom_blob"),
            ],
            errors: Vec::new(),
        }
    }

    #[test]
    fn classifies_known_source_kinds_and_reviews_unknowns() {
        let bundle = classify_bronze_candidate_preview_bundle(
            &preview_bundle(),
            "v250_test_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert_eq!(bundle.schema, "omnibet.bronze_preview_classification_bundle.v250");
        assert_eq!(bundle.total_rows, 4);
        assert_eq!(bundle.classified_rows, 3);
        assert_eq!(bundle.review_required_rows, 1);
        assert!(bundle.quarantine_only);
        assert!(!bundle.import_allowed_now);
        assert!(!bundle.promotion_allowed);
        assert!(!bundle.evaluation_allowed);
        assert!(!bundle.training_dataset_promotion_allowed);
        assert!(bundle.rows.iter().any(|row| row.row_class == "fixture_result"));
        assert!(bundle.rows.iter().any(|row| row.row_class == "odds_snapshot"));
        assert!(bundle.rows.iter().any(|row| row.row_class == "lineup_event_context"));
        assert!(bundle.rows.iter().any(|row| row.classification_status == "review_required"));
    }

    #[test]
    fn classified_rows_keep_all_safety_flags_locked() {
        let bundle = classify_bronze_candidate_preview_bundle(
            &preview_bundle(),
            "v250_test_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert!(bundle.rows.iter().all(|row| row.quarantine_only));
        assert!(bundle.rows.iter().all(|row| !row.import_allowed_now));
        assert!(bundle.rows.iter().all(|row| !row.promotion_allowed));
        assert!(bundle.rows.iter().all(|row| !row.evaluation_allowed));
        assert!(bundle.rows.iter().all(|row| !row.training_dataset_promotion_allowed));
    }
}
