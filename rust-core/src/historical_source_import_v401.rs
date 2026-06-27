use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalFixtureRowV401 {
    pub fixture_id: String,
    pub source_id: String,
    pub competition: String,
    pub season: String,
    pub kickoff_utc: String,
    pub home_team_raw: String,
    pub away_team_raw: String,
    pub home_team_canonical_id: String,
    pub away_team_canonical_id: String,
    pub final_home_score: i64,
    pub final_away_score: i64,
    pub result_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalOddsRowV401 {
    pub fixture_id: String,
    pub source_id: String,
    pub market_family: String,
    pub market_id: String,
    pub selection_id: String,
    pub selection_raw: String,
    pub bookmaker: String,
    pub captured_at_utc: String,
    pub decimal_odds: f64,
    pub is_closing_snapshot: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalSettlementRowV401 {
    pub fixture_id: String,
    pub market_family: String,
    pub selection_id: String,
    pub settled_at_utc: String,
    pub settlement_result: String,
    pub label_available_after_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalIdentityRowV401 {
    pub entity_type: String,
    pub source_id: String,
    pub raw_name: String,
    pub canonical_id: String,
    pub canonical_name: String,
    pub confidence: f64,
    pub review_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalImportValidationReportV401 {
    pub schema: String,
    pub paper_only: bool,
    pub status: String,
    pub source_manifest_verified: bool,
    pub fixture_rows: usize,
    pub odds_rows: usize,
    pub settlement_rows: usize,
    pub identity_rows: usize,
    pub validation_errors: Vec<String>,
    pub validation_warnings: Vec<String>,
    pub ready_for_materialization: bool,
    pub ready_for_training: bool,
    pub trust_status: String,
    pub credential_values_present: bool,
    pub recommendation_output_present: bool,
}

#[derive(Debug, Clone)]
pub struct HistoricalImportPathsV401 {
    pub manifest: PathBuf,
    pub fixtures: PathBuf,
    pub odds: PathBuf,
    pub settlements: PathBuf,
    pub identities: PathBuf,
}

pub fn default_historical_import_paths(root: &Path) -> HistoricalImportPathsV401 {
    let base = root.join("data/historical/v401_v410");
    HistoricalImportPathsV401 {
        manifest: base.join("historical_import.sample.json"),
        fixtures: base.join("fixtures.sample.json"),
        odds: base.join("odds.sample.json"),
        settlements: base.join("settlements.sample.json"),
        identities: base.join("identity_map.sample.json"),
    }
}

fn read_json(path: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    serde_json::from_str::<Value>(&text).map_err(|e| format!("parse {}: {e}", path.display()))
}

fn read_rows<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<Vec<T>, String> {
    let value = read_json(path)?;
    let rows = value
        .get("rows")
        .cloned()
        .ok_or_else(|| format!("{} missing rows", path.display()))?;
    serde_json::from_value::<Vec<T>>(rows).map_err(|e| format!("decode {} rows: {e}", path.display()))
}

pub fn parse_historical_import_contract(root: &Path) -> Result<Value, String> {
    read_json(&root.join("configs/historical_source_import.v401_v410.json"))
}

pub fn validate_historical_import_contract(root: &Path) -> Result<(), String> {
    let contract = parse_historical_import_contract(root)?;
    if contract.get("schema").and_then(Value::as_str) != Some("omnibet.historical_source_import_contract.v401_v410") {
        return Err("unexpected historical import contract schema".to_string());
    }
    if contract.get("paper_only").and_then(Value::as_bool) != Some(true) {
        return Err("historical import contract must be paper_only".to_string());
    }
    if contract.get("live_provider_calls_allowed").and_then(Value::as_bool) != Some(false) {
        return Err("historical import contract must forbid live provider calls".to_string());
    }
    if contract.get("training_allowed").and_then(Value::as_bool) != Some(false) {
        return Err("v401-v410 must not allow training".to_string());
    }
    Ok(())
}

fn is_after_or_equal(left: &str, right: &str) -> bool {
    left >= right
}

fn is_before_or_equal(left: &str, right: &str) -> bool {
    left <= right
}

pub fn validate_historical_import_pack(
    fixtures: &[HistoricalFixtureRowV401],
    odds: &[HistoricalOddsRowV401],
    settlements: &[HistoricalSettlementRowV401],
    identities: &[HistoricalIdentityRowV401],
    source_manifest_verified: bool,
) -> HistoricalImportValidationReportV401 {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();
    let mut fixture_ids = HashSet::new();
    let mut kickoff_by_fixture: HashMap<&str, &str> = HashMap::new();

    for fixture in fixtures {
        if !fixture_ids.insert(fixture.fixture_id.as_str()) {
            errors.push(format!("duplicate_fixture_id:{}", fixture.fixture_id));
        }
        if fixture.result_status != "final" {
            warnings.push(format!("non_final_fixture:{}", fixture.fixture_id));
        }
        kickoff_by_fixture.insert(fixture.fixture_id.as_str(), fixture.kickoff_utc.as_str());
    }

    for row in odds {
        match kickoff_by_fixture.get(row.fixture_id.as_str()) {
            Some(kickoff) => {
                if row.is_closing_snapshot && !is_before_or_equal(&row.captured_at_utc, kickoff) {
                    errors.push(format!("odds_after_kickoff:{}:{}", row.fixture_id, row.selection_id));
                }
            }
            None => errors.push(format!("odds_missing_fixture:{}", row.fixture_id)),
        }
        if row.decimal_odds <= 1.0 || !row.decimal_odds.is_finite() {
            errors.push(format!("invalid_decimal_odds:{}:{}", row.fixture_id, row.selection_id));
        }
    }

    for row in settlements {
        match kickoff_by_fixture.get(row.fixture_id.as_str()) {
            Some(kickoff) => {
                if !is_after_or_equal(&row.label_available_after_utc, kickoff) {
                    errors.push(format!("label_before_kickoff:{}:{}", row.fixture_id, row.selection_id));
                }
            }
            None => errors.push(format!("settlement_missing_fixture:{}", row.fixture_id)),
        }
        if !matches!(row.settlement_result.as_str(), "win" | "loss" | "push" | "void") {
            errors.push(format!("invalid_settlement_result:{}:{}", row.fixture_id, row.selection_id));
        }
    }

    for row in identities {
        if row.confidence < 0.80 && row.review_status != "needs_review" {
            errors.push(format!("low_confidence_identity_without_review:{}", row.raw_name));
        }
        if row.canonical_id.is_empty() || row.raw_name.is_empty() {
            errors.push(format!("empty_identity_field:{}", row.raw_name));
        }
    }

    if !source_manifest_verified {
        warnings.push("source_manifest_hashes_placeholder_or_not_verified".to_string());
    }

    let ok = errors.is_empty();
    HistoricalImportValidationReportV401 {
        schema: "omnibet.historical_import_validation_report.v401_v410".to_string(),
        paper_only: true,
        status: if ok { "validated_for_materialization".to_string() } else { "blocked_import_validation".to_string() },
        source_manifest_verified,
        fixture_rows: fixtures.len(),
        odds_rows: odds.len(),
        settlement_rows: settlements.len(),
        identity_rows: identities.len(),
        validation_errors: errors,
        validation_warnings: warnings,
        ready_for_materialization: ok,
        ready_for_training: false,
        trust_status: "sample_only".to_string(),
        credential_values_present: false,
        recommendation_output_present: false,
    }
}

pub fn load_and_validate_historical_import(root: &Path) -> Result<HistoricalImportValidationReportV401, String> {
    validate_historical_import_contract(root)?;
    let paths = default_historical_import_paths(root);
    let manifest = read_json(&paths.manifest)?;
    let source_manifest_verified = manifest
        .get("schema")
        .and_then(Value::as_str)
        == Some("omnibet.historical_import_manifest.v401_v410");
    let fixtures = read_rows::<HistoricalFixtureRowV401>(&paths.fixtures)?;
    let odds = read_rows::<HistoricalOddsRowV401>(&paths.odds)?;
    let settlements = read_rows::<HistoricalSettlementRowV401>(&paths.settlements)?;
    let identities = read_rows::<HistoricalIdentityRowV401>(&paths.identities)?;
    Ok(validate_historical_import_pack(
        &fixtures,
        &odds,
        &settlements,
        &identities,
        source_manifest_verified,
    ))
}

pub fn write_historical_import_validation_report(path: &Path, report: &HistoricalImportValidationReportV401) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(report).map_err(|e| format!("serialize historical import report: {e}"))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> HistoricalFixtureRowV401 {
        HistoricalFixtureRowV401 {
            fixture_id: "fixture:test".to_string(),
            source_id: "source".to_string(),
            competition: "League".to_string(),
            season: "2024".to_string(),
            kickoff_utc: "2024-01-01T12:00:00Z".to_string(),
            home_team_raw: "Home".to_string(),
            away_team_raw: "Away".to_string(),
            home_team_canonical_id: "team:home".to_string(),
            away_team_canonical_id: "team:away".to_string(),
            final_home_score: 1,
            final_away_score: 0,
            result_status: "final".to_string(),
        }
    }

    #[test]
    fn validates_safe_historical_import_pack() {
        let odds = vec![HistoricalOddsRowV401 {
            fixture_id: "fixture:test".to_string(),
            source_id: "source".to_string(),
            market_family: "1x2".to_string(),
            market_id: "football_1x2_regulation".to_string(),
            selection_id: "home".to_string(),
            selection_raw: "Home".to_string(),
            bookmaker: "Book".to_string(),
            captured_at_utc: "2024-01-01T11:55:00Z".to_string(),
            decimal_odds: 1.8,
            is_closing_snapshot: true,
        }];
        let settlements = vec![HistoricalSettlementRowV401 {
            fixture_id: "fixture:test".to_string(),
            market_family: "1x2".to_string(),
            selection_id: "home".to_string(),
            settled_at_utc: "2024-01-01T14:00:00Z".to_string(),
            settlement_result: "win".to_string(),
            label_available_after_utc: "2024-01-01T14:00:00Z".to_string(),
        }];
        let identities = vec![HistoricalIdentityRowV401 {
            entity_type: "team".to_string(),
            source_id: "source".to_string(),
            raw_name: "Home".to_string(),
            canonical_id: "team:home".to_string(),
            canonical_name: "Home".to_string(),
            confidence: 1.0,
            review_status: "accepted".to_string(),
        }];
        let report = validate_historical_import_pack(&[fixture()], &odds, &settlements, &identities, true);
        assert_eq!(report.status, "validated_for_materialization");
        assert!(report.ready_for_materialization);
        assert!(!report.ready_for_training);
        assert_eq!(report.trust_status, "sample_only");
        assert!(!report.recommendation_output_present);
    }

    #[test]
    fn blocks_odds_after_kickoff() {
        let odds = vec![HistoricalOddsRowV401 {
            fixture_id: "fixture:test".to_string(),
            source_id: "source".to_string(),
            market_family: "1x2".to_string(),
            market_id: "football_1x2_regulation".to_string(),
            selection_id: "home".to_string(),
            selection_raw: "Home".to_string(),
            bookmaker: "Book".to_string(),
            captured_at_utc: "2024-01-01T12:05:00Z".to_string(),
            decimal_odds: 1.8,
            is_closing_snapshot: true,
        }];
        let report = validate_historical_import_pack(&[fixture()], &odds, &[], &[], true);
        assert_eq!(report.status, "blocked_import_validation");
        assert!(report.validation_errors.iter().any(|e| e.contains("odds_after_kickoff")));
    }
}
