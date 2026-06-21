use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProviderNormalizationPreviewBundleV255 {
    pub schema: String,
    pub bundle_id: String,
    pub created_at: String,
    pub paper_only: bool,
    pub quarantine_only: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
    pub total_rows: usize,
    pub row_counts: BTreeMap<String, usize>,
    pub rows: Vec<ProviderNormalizedPreviewRowV255>,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProviderNormalizedPreviewRowV255 {
    pub row_id: String,
    pub row_type: String,
    pub provider_id: String,
    pub fixture_id: String,
    pub fields: BTreeMap<String, String>,
    pub price_decimal: Option<f64>,
    pub quarantine_only: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
}

pub fn build_provider_normalization_preview_v255(
    odds_fixture_text: &str,
    football_fixture_text: &str,
    bundle_id: &str,
    created_at: &str,
) -> Result<ProviderNormalizationPreviewBundleV255, String> {
    let odds = serde_json::from_str::<Value>(odds_fixture_text)
        .map_err(|err| format!("parse odds fixture: {}", err))?;
    let football = serde_json::from_str::<Value>(football_fixture_text)
        .map_err(|err| format!("parse football fixture: {}", err))?;
    let mut rows = Vec::new();
    let mut blockers = Vec::new();
    rows.extend(normalize_odds_fixture(&odds, &mut blockers));
    rows.extend(normalize_football_fixture(&football, &mut blockers));

    let mut row_counts = BTreeMap::new();
    for row in &rows {
        *row_counts.entry(row.row_type.clone()).or_insert(0) += 1;
    }

    Ok(ProviderNormalizationPreviewBundleV255 {
        schema: "omnibet.provider_normalization_preview_bundle.v255".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        paper_only: true,
        quarantine_only: true,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
        total_rows: rows.len(),
        row_counts,
        rows,
        blockers,
    })
}

fn normalize_odds_fixture(value: &Value, blockers: &mut Vec<String>) -> Vec<ProviderNormalizedPreviewRowV255> {
    let Some(fixtures) = value.as_array() else {
        blockers.push("odds fixture root must be an array".to_string());
        return Vec::new();
    };
    let mut rows = Vec::new();
    for fixture in fixtures {
        let fixture_id = string_at(fixture, &["id"]).unwrap_or_else(|| "unknown_fixture".to_string());
        let commence_time = string_at(fixture, &["commence_time"]).unwrap_or_default();
        let bookmakers = fixture.get("bookmakers").and_then(Value::as_array).cloned().unwrap_or_default();
        for bookmaker in bookmakers {
            let bookmaker_id = string_at(&bookmaker, &["key"]).unwrap_or_else(|| "unknown_bookmaker".to_string());
            let snapshot_utc = string_at(&bookmaker, &["last_update"]).unwrap_or_else(|| commence_time.clone());
            let markets = bookmaker.get("markets").and_then(Value::as_array).cloned().unwrap_or_default();
            for market in markets {
                let market_key = string_at(&market, &["key"]).unwrap_or_else(|| "unknown_market".to_string());
                let outcomes = market.get("outcomes").and_then(Value::as_array).cloned().unwrap_or_default();
                for outcome in outcomes {
                    let selection_key = string_at(&outcome, &["name"]).unwrap_or_else(|| "unknown_selection".to_string());
                    let price_decimal = number_at(&outcome, &["price"]);
                    let mut fields = BTreeMap::new();
                    fields.insert("fixture_id".to_string(), fixture_id.clone());
                    fields.insert("provider_id".to_string(), "the_odds_api".to_string());
                    fields.insert("bookmaker_id".to_string(), bookmaker_id.clone());
                    fields.insert("market_key".to_string(), market_key.clone());
                    fields.insert("selection_key".to_string(), selection_key.clone());
                    fields.insert("price_decimal".to_string(), price_decimal.map(|price| price.to_string()).unwrap_or_default());
                    fields.insert("snapshot_utc".to_string(), snapshot_utc.clone());
                    rows.push(ProviderNormalizedPreviewRowV255 {
                        row_id: format!("odds::{}::{}::{}::{}", fixture_id, bookmaker_id, market_key, selection_key),
                        row_type: "odds_snapshot_candidate".to_string(),
                        provider_id: "the_odds_api".to_string(),
                        fixture_id: fixture_id.clone(),
                        fields,
                        price_decimal,
                        quarantine_only: true,
                        promotion_allowed: false,
                        evaluation_allowed: false,
                        training_dataset_promotion_allowed: false,
                    });
                }
            }
        }
    }
    if rows.is_empty() {
        blockers.push("odds fixture produced no normalized rows".to_string());
    }
    rows
}

fn normalize_football_fixture(value: &Value, blockers: &mut Vec<String>) -> Vec<ProviderNormalizedPreviewRowV255> {
    let Some(fixtures) = value.get("response").and_then(Value::as_array) else {
        blockers.push("football fixture response must be an array".to_string());
        return Vec::new();
    };
    let mut rows = Vec::new();
    for fixture in fixtures {
        let fixture_id = number_at(fixture, &["fixture", "id"]).map(|value| value.to_string()).unwrap_or_else(|| "unknown_fixture".to_string());
        let kickoff_utc = string_at(fixture, &["fixture", "date"]).unwrap_or_default();
        let home_team_id = number_at(fixture, &["teams", "home", "id"]).map(|value| value.to_string()).unwrap_or_default();
        let away_team_id = number_at(fixture, &["teams", "away", "id"]).map(|value| value.to_string()).unwrap_or_default();
        let home_goals = number_at(fixture, &["goals", "home"]).map(|value| value.to_string()).unwrap_or_default();
        let away_goals = number_at(fixture, &["goals", "away"]).map(|value| value.to_string()).unwrap_or_default();
        let result_status = string_at(fixture, &["fixture", "status", "short"]).unwrap_or_else(|| "unknown".to_string());
        let mut fields = BTreeMap::new();
        fields.insert("fixture_id".to_string(), fixture_id.clone());
        fields.insert("provider_id".to_string(), "api_football".to_string());
        fields.insert("home_team_id".to_string(), home_team_id);
        fields.insert("away_team_id".to_string(), away_team_id);
        fields.insert("kickoff_utc".to_string(), kickoff_utc.clone());
        fields.insert("home_goals".to_string(), home_goals);
        fields.insert("away_goals".to_string(), away_goals);
        fields.insert("result_status".to_string(), result_status);
        rows.push(ProviderNormalizedPreviewRowV255 {
            row_id: format!("fixture_result::{}", fixture_id),
            row_type: "fixture_result_candidate".to_string(),
            provider_id: "api_football".to_string(),
            fixture_id: fixture_id.clone(),
            fields,
            price_decimal: None,
            quarantine_only: true,
            promotion_allowed: false,
            evaluation_allowed: false,
            training_dataset_promotion_allowed: false,
        });

        let events = fixture.get("events").and_then(Value::as_array).cloned().unwrap_or_default();
        for (idx, event) in events.iter().enumerate() {
            let elapsed_minute = number_at(event, &["time", "elapsed"]).map(|value| value.to_string()).unwrap_or_default();
            let team_id = number_at(event, &["team", "id"]).map(|value| value.to_string()).unwrap_or_default();
            let player_id = number_at(event, &["player", "id"]).map(|value| value.to_string()).unwrap_or_default();
            let event_type = string_at(event, &["type"]).unwrap_or_else(|| "unknown".to_string());
            let mut event_fields = BTreeMap::new();
            event_fields.insert("fixture_id".to_string(), fixture_id.clone());
            event_fields.insert("provider_id".to_string(), "api_football".to_string());
            event_fields.insert("team_id".to_string(), team_id);
            event_fields.insert("player_id".to_string(), player_id);
            event_fields.insert("event_type".to_string(), event_type);
            event_fields.insert("elapsed_minute".to_string(), elapsed_minute);
            event_fields.insert("observed_at_utc".to_string(), kickoff_utc.clone());
            rows.push(ProviderNormalizedPreviewRowV255 {
                row_id: format!("event_context::{}::{}", fixture_id, idx + 1),
                row_type: "event_context_candidate".to_string(),
                provider_id: "api_football".to_string(),
                fixture_id: fixture_id.clone(),
                fields: event_fields,
                price_decimal: None,
                quarantine_only: true,
                promotion_allowed: false,
                evaluation_allowed: false,
                training_dataset_promotion_allowed: false,
            });
        }
    }
    if rows.is_empty() {
        blockers.push("football fixture produced no normalized rows".to_string());
    }
    rows
}

fn string_at(value: &Value, path: &[&str]) -> Option<String> {
    let mut current = value;
    for part in path {
        current = current.get(*part)?;
    }
    current.as_str().map(str::to_string)
}

fn number_at(value: &Value, path: &[&str]) -> Option<f64> {
    let mut current = value;
    for part in path {
        current = current.get(*part)?;
    }
    current.as_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_offline_provider_fixtures_to_preview_rows() {
        let bundle = build_provider_normalization_preview_v255(
            include_str!("../../data/provider_fixtures/v254/odds_provider_snapshot.sample.json"),
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
            "v255_test_bundle",
            "2026-06-21T00:00:00Z",
        )
        .expect("build normalization preview");
        assert_eq!(bundle.schema, "omnibet.provider_normalization_preview_bundle.v255");
        assert!(bundle.blockers.is_empty(), "{:?}", bundle.blockers);
        assert_eq!(bundle.row_counts["odds_snapshot_candidate"], 3);
        assert_eq!(bundle.row_counts["fixture_result_candidate"], 1);
        assert_eq!(bundle.row_counts["event_context_candidate"], 1);
        assert_eq!(bundle.total_rows, 5);
        assert!(bundle.rows.iter().all(|row| row.quarantine_only));
        assert!(bundle.rows.iter().all(|row| !row.evaluation_allowed));
        assert!(bundle.rows.iter().any(|row| row.row_type == "odds_snapshot_candidate" && row.price_decimal == Some(1.35)));
    }

    #[test]
    fn malformed_fixture_blocks_without_unlocking_safety() {
        let bundle = build_provider_normalization_preview_v255(
            "{}",
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
            "v255_bad_bundle",
            "2026-06-21T00:00:00Z",
        )
        .expect("build normalization preview");
        assert!(!bundle.blockers.is_empty());
        assert!(bundle.quarantine_only);
        assert!(!bundle.promotion_allowed);
        assert!(!bundle.evaluation_allowed);
        assert!(!bundle.training_dataset_promotion_allowed);
    }
}
