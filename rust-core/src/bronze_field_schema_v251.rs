use crate::{BronzePreviewClassificationBundle, BronzePreviewClassificationRow};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewFieldSchemaBundle {
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
    pub schema_ok_rows: u64,
    pub review_required_rows: u64,
    pub rows: Vec<BronzePreviewFieldSchemaRow>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzePreviewFieldSchemaRow {
    pub row_id: String,
    pub row_class: String,
    pub schema_status: String,
    pub required_fields: Vec<String>,
    pub present_fields: Vec<String>,
    pub missing_fields: Vec<String>,
    pub review_reason: Option<String>,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
}

pub fn validate_bronze_preview_field_schema_bundle(
    source: &BronzePreviewClassificationBundle,
    present_fields_by_row_id: &BTreeMap<String, Vec<String>>,
    bundle_id: &str,
    created_at: &str,
) -> BronzePreviewFieldSchemaBundle {
    let mut rows = Vec::new();
    let mut schema_ok_rows = 0u64;
    let mut review_required_rows = 0u64;

    for row in &source.rows {
        let present_fields = present_fields_by_row_id
            .get(&row.row_id)
            .cloned()
            .unwrap_or_default();
        let checked = validate_bronze_preview_field_schema_row(row, &present_fields);
        if checked.schema_status == "schema_ok" {
            schema_ok_rows += 1;
        } else {
            review_required_rows += 1;
        }
        rows.push(checked);
    }

    BronzePreviewFieldSchemaBundle {
        schema: "omnibet.bronze_preview_field_schema_bundle.v251".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        source_bundle_id: source.bundle_id.clone(),
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
        total_rows: rows.len() as u64,
        schema_ok_rows,
        review_required_rows,
        rows,
    }
}

pub fn validate_bronze_preview_field_schema_row(
    row: &BronzePreviewClassificationRow,
    present_fields: &[String],
) -> BronzePreviewFieldSchemaRow {
    let required = required_fields_for_row_class(&row.row_class);
    let mut required_fields: Vec<String> = required.iter().map(|field| field.to_string()).collect();
    required_fields.sort();
    let mut present_fields_vec = present_fields.to_vec();
    present_fields_vec.sort();
    present_fields_vec.dedup();
    let present_set: BTreeSet<&str> = present_fields_vec.iter().map(|field| field.as_str()).collect();
    let missing_fields: Vec<String> = required_fields
        .iter()
        .filter(|field| !present_set.contains(field.as_str()))
        .cloned()
        .collect();

    let (schema_status, review_reason) = if row.classification_status != "classified" {
        (
            "review_required".to_string(),
            Some("row classification is not accepted yet".to_string()),
        )
    } else if required_fields.is_empty() {
        (
            "review_required".to_string(),
            Some(format!("no schema rules for row class: {}", row.row_class)),
        )
    } else if missing_fields.is_empty() {
        ("schema_ok".to_string(), None)
    } else {
        (
            "review_required".to_string(),
            Some(format!("missing required fields: {}", missing_fields.join(","))),
        )
    };

    BronzePreviewFieldSchemaRow {
        row_id: row.row_id.clone(),
        row_class: row.row_class.clone(),
        schema_status,
        required_fields,
        present_fields: present_fields_vec,
        missing_fields,
        review_reason,
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
    }
}

pub fn required_fields_for_row_class(row_class: &str) -> Vec<&'static str> {
    match row_class {
        "fixture_result" => vec!["fixture_id", "home_team", "away_team", "kickoff_utc", "result_status"],
        "odds_snapshot" => vec![
            "fixture_id",
            "provider_id",
            "bookmaker_id",
            "market_key",
            "selection_key",
            "price_decimal",
            "snapshot_utc",
        ],
        "lineup_event_context" => vec![
            "fixture_id",
            "provider_id",
            "entity_id",
            "event_type",
            "observed_at_utc",
        ],
        _ => Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::BronzePreviewClassificationRow;

    fn classified_row(row_id: &str, row_class: &str) -> BronzePreviewClassificationRow {
        BronzePreviewClassificationRow {
            row_id: row_id.to_string(),
            task_id: format!("task_{}", row_id),
            source_id: format!("source_{}", row_id),
            source_kind: "odds".to_string(),
            row_class: row_class.to_string(),
            classification_status: "classified".to_string(),
            review_reason: None,
            raw_line_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_string(),
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
        }
    }

    fn review_row(row_id: &str) -> BronzePreviewClassificationRow {
        let mut row = classified_row(row_id, "unknown");
        row.classification_status = "review_required".to_string();
        row.review_reason = Some("unknown source kind".to_string());
        row
    }

    fn classification_bundle() -> BronzePreviewClassificationBundle {
        BronzePreviewClassificationBundle {
            schema: "omnibet.bronze_preview_classification_bundle.v250".to_string(),
            bundle_id: "v250_test_bundle".to_string(),
            created_at: "2026-06-21T00:00:00Z".to_string(),
            source_bundle_id: "v249_test_bundle".to_string(),
            quarantine_only: true,
            import_allowed_now: false,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
            total_rows: 3,
            classified_rows: 2,
            review_required_rows: 1,
            rows: vec![
                classified_row("odds_ok", "odds_snapshot"),
                classified_row("fixture_bad", "fixture_result"),
                review_row("unknown_review"),
            ],
        }
    }

    fn fields(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    #[test]
    fn validates_required_fields_and_marks_review_rows() {
        let mut present = BTreeMap::new();
        present.insert(
            "odds_ok".to_string(),
            fields(&[
                "fixture_id",
                "provider_id",
                "bookmaker_id",
                "market_key",
                "selection_key",
                "price_decimal",
                "snapshot_utc",
            ]),
        );
        present.insert(
            "fixture_bad".to_string(),
            fields(&["fixture_id", "home_team", "away_team"]),
        );
        let bundle = validate_bronze_preview_field_schema_bundle(
            &classification_bundle(),
            &present,
            "v251_test_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert_eq!(bundle.schema, "omnibet.bronze_preview_field_schema_bundle.v251");
        assert_eq!(bundle.total_rows, 3);
        assert_eq!(bundle.schema_ok_rows, 1);
        assert_eq!(bundle.review_required_rows, 2);
        assert!(bundle.rows.iter().any(|row| row.row_id == "odds_ok" && row.schema_status == "schema_ok"));
        assert!(bundle.rows.iter().any(|row| row.row_id == "fixture_bad" && row.missing_fields.contains(&"kickoff_utc".to_string())));
        assert!(bundle.rows.iter().any(|row| row.row_id == "unknown_review" && row.schema_status == "review_required"));
    }

    #[test]
    fn field_schema_rows_keep_all_safety_flags_locked() {
        let bundle = validate_bronze_preview_field_schema_bundle(
            &classification_bundle(),
            &BTreeMap::new(),
            "v251_test_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert!(bundle.quarantine_only);
        assert!(!bundle.import_allowed_now);
        assert!(!bundle.promotion_allowed);
        assert!(!bundle.evaluation_allowed);
        assert!(!bundle.training_dataset_promotion_allowed);
        assert!(bundle.rows.iter().all(|row| row.quarantine_only));
        assert!(bundle.rows.iter().all(|row| !row.training_dataset_promotion_allowed));
    }
}
