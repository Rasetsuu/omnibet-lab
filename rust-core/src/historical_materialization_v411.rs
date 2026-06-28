use crate::historical_source_import_v401::{
    load_and_validate_historical_import, HistoricalFixtureRowV401, HistoricalIdentityRowV401,
    HistoricalOddsRowV401, HistoricalSettlementRowV401,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BronzeFixtureImportRowV411 {
    pub fixture_id: String,
    pub source_id: String,
    pub competition: String,
    pub season: String,
    pub kickoff_utc: String,
    pub home_team_raw: String,
    pub away_team_raw: String,
    pub result_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BronzeOddsImportRowV411 {
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
pub struct BronzeSettlementImportRowV411 {
    pub fixture_id: String,
    pub market_family: String,
    pub selection_id: String,
    pub settled_at_utc: String,
    pub settlement_result: String,
    pub label_available_after_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SilverFixtureRowV411 {
    pub fixture_id: String,
    pub competition: String,
    pub season: String,
    pub kickoff_utc: String,
    pub home_team_id: String,
    pub away_team_id: String,
    pub home_team_name: String,
    pub away_team_name: String,
    pub result_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SilverOddsRowV411 {
    pub fixture_id: String,
    pub market_family: String,
    pub market_id: String,
    pub selection_id: String,
    pub bookmaker: String,
    pub captured_at_utc: String,
    pub decimal_odds: f64,
    pub no_vig_group_key: String,
    pub is_closing_snapshot: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoldEvaluationCandidateRowV411 {
    pub candidate_id: String,
    pub fixture_id: String,
    pub prediction_time_utc: String,
    pub label_available_after_utc: String,
    pub market_family: String,
    pub selection_id: String,
    pub decimal_odds: f64,
    pub settlement_result: String,
    pub feature_leakage_safe: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaterializedTableSummaryV411 {
    pub table_id: String,
    pub row_count: usize,
    pub status: String,
    pub preview_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalMaterializationManifestV411 {
    pub schema: String,
    pub paper_only: bool,
    pub status: String,
    pub bronze_tables: Vec<MaterializedTableSummaryV411>,
    pub silver_tables: Vec<MaterializedTableSummaryV411>,
    pub gold_tables: Vec<MaterializedTableSummaryV411>,
    pub content_hashes_present: bool,
    pub preferred_large_scale_codec: String,
    pub future_large_scale_codec: String,
    pub ready_for_training: bool,
    pub credential_values_present: bool,
    pub recommendation_output_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalMaterializationReportV411 {
    pub schema: String,
    pub paper_only: bool,
    pub status: String,
    pub source_import_status: String,
    pub bronze_fixture_rows: usize,
    pub bronze_odds_rows: usize,
    pub bronze_settlement_rows: usize,
    pub silver_fixture_rows: usize,
    pub silver_odds_rows: usize,
    pub gold_candidate_rows: usize,
    pub materialization_manifest: HistoricalMaterializationManifestV411,
    pub ready_for_walk_forward: bool,
    pub ready_for_training: bool,
    pub trust_status: String,
    pub validation_errors: Vec<String>,
    pub credential_values_present: bool,
    pub recommendation_output_present: bool,
}

#[derive(Debug, Clone)]
pub struct HistoricalMaterializationOutputsV411 {
    pub report: PathBuf,
    pub bronze_fixtures: PathBuf,
    pub bronze_odds: PathBuf,
    pub bronze_settlements: PathBuf,
    pub silver_fixtures: PathBuf,
    pub silver_odds: PathBuf,
    pub gold_candidates: PathBuf,
    pub manifest: PathBuf,
}

pub fn default_historical_materialization_outputs_v411(root: &Path) -> HistoricalMaterializationOutputsV411 {
    let base = root.join("reports/materialized/v411_v420");
    HistoricalMaterializationOutputsV411 {
        report: root.join("reports/historical_materialization_v411_v420_report.json"),
        bronze_fixtures: base.join("bronze_fixtures.preview.json"),
        bronze_odds: base.join("bronze_odds.preview.json"),
        bronze_settlements: base.join("bronze_settlements.preview.json"),
        silver_fixtures: base.join("silver_fixtures.preview.json"),
        silver_odds: base.join("silver_odds.preview.json"),
        gold_candidates: base.join("gold_evaluation_candidates.preview.json"),
        manifest: base.join("materialization_manifest.json"),
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

pub fn parse_historical_materialization_contract_v411(root: &Path) -> Result<Value, String> {
    read_json(&root.join("configs/historical_materialization.v411_v420.json"))
}

pub fn validate_historical_materialization_contract_v411(root: &Path) -> Result<(), String> {
    let contract = parse_historical_materialization_contract_v411(root)?;
    if contract.get("schema").and_then(Value::as_str) != Some("omnibet.historical_materialization_contract.v411_v420") {
        return Err("unexpected historical materialization contract schema".to_string());
    }
    if contract.get("paper_only").and_then(Value::as_bool) != Some(true) {
        return Err("historical materialization must remain paper_only".to_string());
    }
    if contract.get("live_provider_calls_allowed").and_then(Value::as_bool) != Some(false) {
        return Err("historical materialization must forbid live provider calls".to_string());
    }
    if contract.get("training_allowed").and_then(Value::as_bool) != Some(false) {
        return Err("v411-v420 must not allow training".to_string());
    }
    Ok(())
}

fn identity_lookup(identities: &[HistoricalIdentityRowV401]) -> HashMap<String, (String, String)> {
    identities
        .iter()
        .map(|row| (row.raw_name.clone(), (row.canonical_id.clone(), row.canonical_name.clone())))
        .collect()
}

pub fn build_bronze_fixture_rows_v411(fixtures: &[HistoricalFixtureRowV401]) -> Vec<BronzeFixtureImportRowV411> {
    fixtures
        .iter()
        .map(|row| BronzeFixtureImportRowV411 {
            fixture_id: row.fixture_id.clone(),
            source_id: row.source_id.clone(),
            competition: row.competition.clone(),
            season: row.season.clone(),
            kickoff_utc: row.kickoff_utc.clone(),
            home_team_raw: row.home_team_raw.clone(),
            away_team_raw: row.away_team_raw.clone(),
            result_status: row.result_status.clone(),
        })
        .collect()
}

pub fn build_bronze_odds_rows_v411(odds: &[HistoricalOddsRowV401]) -> Vec<BronzeOddsImportRowV411> {
    odds
        .iter()
        .map(|row| BronzeOddsImportRowV411 {
            fixture_id: row.fixture_id.clone(),
            source_id: row.source_id.clone(),
            market_family: row.market_family.clone(),
            market_id: row.market_id.clone(),
            selection_id: row.selection_id.clone(),
            selection_raw: row.selection_raw.clone(),
            bookmaker: row.bookmaker.clone(),
            captured_at_utc: row.captured_at_utc.clone(),
            decimal_odds: row.decimal_odds,
            is_closing_snapshot: row.is_closing_snapshot,
        })
        .collect()
}

pub fn build_bronze_settlement_rows_v411(settlements: &[HistoricalSettlementRowV401]) -> Vec<BronzeSettlementImportRowV411> {
    settlements
        .iter()
        .map(|row| BronzeSettlementImportRowV411 {
            fixture_id: row.fixture_id.clone(),
            market_family: row.market_family.clone(),
            selection_id: row.selection_id.clone(),
            settled_at_utc: row.settled_at_utc.clone(),
            settlement_result: row.settlement_result.clone(),
            label_available_after_utc: row.label_available_after_utc.clone(),
        })
        .collect()
}

pub fn build_silver_fixture_rows_v411(
    fixtures: &[HistoricalFixtureRowV401],
    identities: &[HistoricalIdentityRowV401],
) -> Vec<SilverFixtureRowV411> {
    let lookup = identity_lookup(identities);
    fixtures
        .iter()
        .map(|row| {
            let home = lookup
                .get(&row.home_team_raw)
                .cloned()
                .unwrap_or_else(|| (row.home_team_canonical_id.clone(), row.home_team_raw.clone()));
            let away = lookup
                .get(&row.away_team_raw)
                .cloned()
                .unwrap_or_else(|| (row.away_team_canonical_id.clone(), row.away_team_raw.clone()));
            SilverFixtureRowV411 {
                fixture_id: row.fixture_id.clone(),
                competition: row.competition.clone(),
                season: row.season.clone(),
                kickoff_utc: row.kickoff_utc.clone(),
                home_team_id: home.0,
                away_team_id: away.0,
                home_team_name: home.1,
                away_team_name: away.1,
                result_status: row.result_status.clone(),
            }
        })
        .collect()
}

pub fn build_silver_odds_rows_v411(odds: &[HistoricalOddsRowV401]) -> Vec<SilverOddsRowV411> {
    odds
        .iter()
        .map(|row| SilverOddsRowV411 {
            fixture_id: row.fixture_id.clone(),
            market_family: row.market_family.clone(),
            market_id: row.market_id.clone(),
            selection_id: row.selection_id.clone(),
            bookmaker: row.bookmaker.clone(),
            captured_at_utc: row.captured_at_utc.clone(),
            decimal_odds: row.decimal_odds,
            no_vig_group_key: format!("{}:{}:{}:{}", row.fixture_id, row.bookmaker, row.market_family, row.captured_at_utc),
            is_closing_snapshot: row.is_closing_snapshot,
        })
        .collect()
}

pub fn build_gold_candidate_rows_v411(
    odds: &[HistoricalOddsRowV401],
    settlements: &[HistoricalSettlementRowV401],
) -> Vec<GoldEvaluationCandidateRowV411> {
    let settlement_lookup: HashMap<String, &HistoricalSettlementRowV401> = settlements
        .iter()
        .map(|row| (format!("{}:{}:{}", row.fixture_id, row.market_family, row.selection_id), row))
        .collect();
    odds
        .iter()
        .filter_map(|row| {
            let key = format!("{}:{}:{}", row.fixture_id, row.market_family, row.selection_id);
            let settlement = settlement_lookup.get(&key)?;
            Some(GoldEvaluationCandidateRowV411 {
                candidate_id: format!("candidate:{}:{}", row.fixture_id, row.selection_id),
                fixture_id: row.fixture_id.clone(),
                prediction_time_utc: row.captured_at_utc.clone(),
                label_available_after_utc: settlement.label_available_after_utc.clone(),
                market_family: row.market_family.clone(),
                selection_id: row.selection_id.clone(),
                decimal_odds: row.decimal_odds,
                settlement_result: settlement.settlement_result.clone(),
                feature_leakage_safe: settlement.label_available_after_utc >= row.captured_at_utc,
            })
        })
        .collect()
}

fn table_summary(table_id: &str, row_count: usize, preview_path: &Path) -> MaterializedTableSummaryV411 {
    MaterializedTableSummaryV411 {
        table_id: table_id.to_string(),
        row_count,
        status: "preview_written".to_string(),
        preview_path: preview_path.to_string_lossy().to_string(),
    }
}

pub fn build_historical_materialization_report_v411(root: &Path) -> Result<HistoricalMaterializationReportV411, String> {
    validate_historical_materialization_contract_v411(root)?;
    let import_report = load_and_validate_historical_import(root)?;
    let base = root.join("data/historical/v401_v410");
    let fixtures = read_rows::<HistoricalFixtureRowV401>(&base.join("fixtures.sample.json"))?;
    let odds = read_rows::<HistoricalOddsRowV401>(&base.join("odds.sample.json"))?;
    let settlements = read_rows::<HistoricalSettlementRowV401>(&base.join("settlements.sample.json"))?;
    let identities = read_rows::<HistoricalIdentityRowV401>(&base.join("identity_map.sample.json"))?;
    let outputs = default_historical_materialization_outputs_v411(root);

    let bronze_fixtures = build_bronze_fixture_rows_v411(&fixtures);
    let bronze_odds = build_bronze_odds_rows_v411(&odds);
    let bronze_settlements = build_bronze_settlement_rows_v411(&settlements);
    let silver_fixtures = build_silver_fixture_rows_v411(&fixtures, &identities);
    let silver_odds = build_silver_odds_rows_v411(&odds);
    let gold_candidates = build_gold_candidate_rows_v411(&odds, &settlements);

    let ok = import_report.ready_for_materialization
        && !gold_candidates.is_empty()
        && gold_candidates.iter().all(|row| row.feature_leakage_safe);

    let manifest = HistoricalMaterializationManifestV411 {
        schema: "omnibet.historical_materialization_manifest.v411_v420".to_string(),
        paper_only: true,
        status: if ok { "materialized_preview".to_string() } else { "blocked_materialization".to_string() },
        bronze_tables: vec![
            table_summary("bronze_fixtures_v411", bronze_fixtures.len(), &outputs.bronze_fixtures),
            table_summary("bronze_odds_v412", bronze_odds.len(), &outputs.bronze_odds),
            table_summary("bronze_settlements_v413", bronze_settlements.len(), &outputs.bronze_settlements),
        ],
        silver_tables: vec![
            table_summary("silver_fixtures_v415", silver_fixtures.len(), &outputs.silver_fixtures),
            table_summary("silver_odds_v416", silver_odds.len(), &outputs.silver_odds),
        ],
        gold_tables: vec![table_summary("gold_evaluation_candidates_v417", gold_candidates.len(), &outputs.gold_candidates)],
        content_hashes_present: false,
        preferred_large_scale_codec: "jsonl.zstd".to_string(),
        future_large_scale_codec: "parquet.zstd".to_string(),
        ready_for_training: false,
        credential_values_present: false,
        recommendation_output_present: false,
    };

    Ok(HistoricalMaterializationReportV411 {
        schema: "omnibet.historical_materialization_report.v411_v420".to_string(),
        paper_only: true,
        status: manifest.status.clone(),
        source_import_status: import_report.status,
        bronze_fixture_rows: bronze_fixtures.len(),
        bronze_odds_rows: bronze_odds.len(),
        bronze_settlement_rows: bronze_settlements.len(),
        silver_fixture_rows: silver_fixtures.len(),
        silver_odds_rows: silver_odds.len(),
        gold_candidate_rows: gold_candidates.len(),
        materialization_manifest: manifest,
        ready_for_walk_forward: ok,
        ready_for_training: false,
        trust_status: "sample_only".to_string(),
        validation_errors: Vec::new(),
        credential_values_present: false,
        recommendation_output_present: false,
    })
}

fn write_json<T: Serialize>(path: &Path, payload: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(payload).map_err(|e| format!("serialize {}: {e}", path.display()))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write {}: {e}", path.display()))
}

pub fn write_historical_materialization_preview_v411(root: &Path) -> Result<HistoricalMaterializationReportV411, String> {
    let report = build_historical_materialization_report_v411(root)?;
    let base = root.join("data/historical/v401_v410");
    let fixtures = read_rows::<HistoricalFixtureRowV401>(&base.join("fixtures.sample.json"))?;
    let odds = read_rows::<HistoricalOddsRowV401>(&base.join("odds.sample.json"))?;
    let settlements = read_rows::<HistoricalSettlementRowV401>(&base.join("settlements.sample.json"))?;
    let identities = read_rows::<HistoricalIdentityRowV401>(&base.join("identity_map.sample.json"))?;
    let outputs = default_historical_materialization_outputs_v411(root);

    write_json(&outputs.bronze_fixtures, &build_bronze_fixture_rows_v411(&fixtures))?;
    write_json(&outputs.bronze_odds, &build_bronze_odds_rows_v411(&odds))?;
    write_json(&outputs.bronze_settlements, &build_bronze_settlement_rows_v411(&settlements))?;
    write_json(&outputs.silver_fixtures, &build_silver_fixture_rows_v411(&fixtures, &identities))?;
    write_json(&outputs.silver_odds, &build_silver_odds_rows_v411(&odds))?;
    write_json(&outputs.gold_candidates, &build_gold_candidate_rows_v411(&odds, &settlements))?;
    write_json(&outputs.manifest, &report.materialization_manifest)?;
    write_json(&outputs.report, &report)?;
    Ok(report)
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
            home_team_raw: "Home FC".to_string(),
            away_team_raw: "Away FC".to_string(),
            home_team_canonical_id: "team:home".to_string(),
            away_team_canonical_id: "team:away".to_string(),
            final_home_score: 2,
            final_away_score: 1,
            result_status: "final".to_string(),
        }
    }

    fn identity_rows() -> Vec<HistoricalIdentityRowV401> {
        vec![
            HistoricalIdentityRowV401 { entity_type: "team".to_string(), source_id: "source".to_string(), raw_name: "Home FC".to_string(), canonical_id: "team:home".to_string(), canonical_name: "Home FC".to_string(), confidence: 1.0, review_status: "accepted".to_string() },
            HistoricalIdentityRowV401 { entity_type: "team".to_string(), source_id: "source".to_string(), raw_name: "Away FC".to_string(), canonical_id: "team:away".to_string(), canonical_name: "Away FC".to_string(), confidence: 1.0, review_status: "accepted".to_string() },
        ]
    }

    #[test]
    fn silver_fixtures_apply_identity_map_v411() {
        let rows = build_silver_fixture_rows_v411(&[fixture()], &identity_rows());
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].home_team_id, "team:home");
        assert_eq!(rows[0].away_team_id, "team:away");
    }

    #[test]
    fn gold_candidates_require_settlements_and_stay_safe_v411() {
        let odds = vec![HistoricalOddsRowV401 { fixture_id: "fixture:test".to_string(), source_id: "source".to_string(), market_family: "1x2".to_string(), market_id: "football_1x2_regulation".to_string(), selection_id: "home".to_string(), selection_raw: "Home FC".to_string(), bookmaker: "Book".to_string(), captured_at_utc: "2024-01-01T11:55:00Z".to_string(), decimal_odds: 1.8, is_closing_snapshot: true }];
        let settlements = vec![HistoricalSettlementRowV401 { fixture_id: "fixture:test".to_string(), market_family: "1x2".to_string(), selection_id: "home".to_string(), settled_at_utc: "2024-01-01T14:00:00Z".to_string(), settlement_result: "win".to_string(), label_available_after_utc: "2024-01-01T14:00:00Z".to_string() }];
        let rows = build_gold_candidate_rows_v411(&odds, &settlements);
        assert_eq!(rows.len(), 1);
        assert!(rows[0].feature_leakage_safe);
        assert_eq!(rows[0].settlement_result, "win");
    }
}
