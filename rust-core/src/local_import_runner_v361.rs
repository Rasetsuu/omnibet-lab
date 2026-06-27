use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LocalSourceManifestEntryV361 {
    pub source_id: String,
    pub local_path: String,
    pub codec: String,
    pub content_sha256: String,
    pub row_count: u64,
    pub observed_at_policy: String,
    pub credential_values_present: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LocalSourceManifestV361 {
    pub schema: String,
    pub generated_at: String,
    pub paper_only: bool,
    pub credential_values_present: bool,
    pub sources: Vec<LocalSourceManifestEntryV361>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalFixtureRowV361 {
    pub canonical_fixture_id: String,
    pub competition_id: String,
    pub season_id: String,
    pub home_team_id: String,
    pub away_team_id: String,
    pub kickoff_at: String,
    pub final_result: String,
    pub settled_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalOddsRowV361 {
    pub canonical_fixture_id: String,
    pub market_family: String,
    pub selection_key: String,
    pub captured_at: String,
    pub price_decimal: f64,
    pub closing_price_decimal: f64,
    pub source_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalSettlementRowV361 {
    pub canonical_fixture_id: String,
    pub market_family: String,
    pub selection_key: String,
    pub outcome: u8,
    pub settled_at: String,
    pub label_created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GeneratedGreenReportV361 {
    pub schema: String,
    pub status: String,
    pub source_manifest_verified: bool,
    pub fixtures_loaded: usize,
    pub odds_rows_loaded: usize,
    pub settlement_rows_loaded: usize,
    pub prediction_rows_generated: usize,
    pub market_families: usize,
    pub storage_manifest_written: bool,
    pub trust_status: String,
    pub validated_paper: bool,
    pub terminal_prediction_allowed: bool,
    pub bilet_builder_allowed: bool,
    pub recommendation_output_present: bool,
}

pub fn parse_local_import_runner_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn parse_source_manifest(text: &str) -> Result<LocalSourceManifestV361, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn parse_jsonl_rows<T>(text: &str) -> Result<Vec<T>, String>
where
    T: for<'de> Deserialize<'de>,
{
    text.lines()
        .filter(|line| !line.trim().is_empty())
        .enumerate()
        .map(|(idx, line)| serde_json::from_str(line).map_err(|e| format!("invalid jsonl line {}: {e}", idx + 1)))
        .collect()
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn string_array_contains(value: &Value, key: &str, expected: &str) -> bool {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|items| items.iter().any(|item| item.as_str() == Some(expected)))
        .unwrap_or(false)
}

fn require_array_items(value: &Value, key: &str, required: &[&str]) -> Result<(), String> {
    for item in required {
        if !string_array_contains(value, key, item) {
            return Err(format!("{key} missing required item: {item}"));
        }
    }
    Ok(())
}

pub fn validate_local_import_runner_contract(contract: &Value) -> Result<(), String> {
    if contract.get("schema").and_then(Value::as_str)
        != Some("omnibet.local_import_runner_contract.v361_v370")
    {
        return Err("unexpected v361-v370 local import runner contract schema".to_string());
    }
    for flag in ["paper_only", "local_first", "sample_only_allowed"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in [
        "live_provider_calls_allowed",
        "credential_values_allowed",
        "real_money_recommendations_allowed",
        "validated_paper_allowed",
    ] {
        if contract.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    require_array_items(
        contract,
        "required_fixture_fields",
        &["canonical_fixture_id", "competition_id", "season_id", "home_team_id", "away_team_id", "kickoff_at", "final_result", "settled_at"],
    )?;
    require_array_items(
        contract,
        "required_odds_fields",
        &["canonical_fixture_id", "market_family", "selection_key", "captured_at", "price_decimal", "closing_price_decimal", "source_id"],
    )?;
    require_array_items(
        contract,
        "required_settlement_fields",
        &["canonical_fixture_id", "market_family", "selection_key", "outcome", "settled_at", "label_created_at"],
    )?;
    require_array_items(
        contract,
        "required_generated_report_fields",
        &["schema", "status", "source_manifest_verified", "walk_forward_report", "baseline_report", "calibration_report", "paper_clv_summary", "trust_gate", "recommendation_output_present"],
    )?;
    let storage = contract.get("storage_contract").and_then(Value::as_object).ok_or_else(|| "storage_contract missing".to_string())?;
    if storage.get("preferred_output_codec").and_then(Value::as_str) != Some("jsonl.zstd") {
        return Err("preferred output codec must be jsonl.zstd".to_string());
    }
    let green = contract.get("green_gate_requirements").and_then(Value::as_object).ok_or_else(|| "green_gate_requirements missing".to_string())?;
    if green.get("trust_status").and_then(Value::as_str) != Some("sample_only") {
        return Err("green gate trust must remain sample_only".to_string());
    }
    if green.get("random_split_used").and_then(Value::as_bool) != Some(false) {
        return Err("random split must remain false".to_string());
    }
    if green.get("recommendation_output_present").and_then(Value::as_bool) != Some(false) {
        return Err("recommendation output must remain false".to_string());
    }
    let acceptance = contract.get("acceptance").and_then(Value::as_object).ok_or_else(|| "acceptance missing".to_string())?;
    for (key, value) in acceptance.iter() {
        if value.as_bool() != Some(true) {
            return Err(format!("acceptance gate not enabled: {key}"));
        }
    }
    Ok(())
}

pub fn validate_source_manifest(manifest: &LocalSourceManifestV361) -> Result<(), String> {
    if manifest.schema != "omnibet.local_import_source_manifest.v361_v370" {
        return Err("unexpected source manifest schema".to_string());
    }
    if !manifest.paper_only {
        return Err("source manifest must be paper_only".to_string());
    }
    if manifest.credential_values_present {
        return Err("source manifest must not contain credential values".to_string());
    }
    if manifest.sources.len() < 3 {
        return Err("source manifest must include at least three sources".to_string());
    }
    for source in &manifest.sources {
        if source.credential_values_present {
            return Err(format!("source {} contains credential values", source.source_id));
        }
        if source.codec != "jsonl" {
            return Err(format!("source {} must use jsonl codec in this mini-pack", source.source_id));
        }
        if source.content_sha256.len() != 64 || !source.content_sha256.chars().all(|c| c.is_ascii_hexdigit()) {
            return Err(format!("source {} content_sha256 must be 64 hex chars", source.source_id));
        }
        if source.row_count == 0 {
            return Err(format!("source {} row_count must be positive", source.source_id));
        }
    }
    Ok(())
}

pub fn verify_manifest_hashes(root: &Path, manifest: &LocalSourceManifestV361) -> Result<bool, String> {
    validate_source_manifest(manifest)?;
    let mut all_match = true;
    for source in &manifest.sources {
        let path = root.join(&source.local_path);
        let bytes = fs::read(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
        let actual = sha256_hex(&bytes);
        if actual != source.content_sha256 {
            all_match = false;
        }
        let text = String::from_utf8(bytes).map_err(|e| format!("decode {} as utf-8: {e}", path.display()))?;
        let rows = text.lines().filter(|line| !line.trim().is_empty()).count() as u64;
        if rows != source.row_count {
            return Err(format!("source {} row_count mismatch: expected {}, got {}", source.source_id, source.row_count, rows));
        }
    }
    Ok(all_match)
}

pub fn build_generated_green_report(
    manifest_hashes_match: bool,
    fixtures: &[LocalFixtureRowV361],
    odds: &[LocalOddsRowV361],
    settlements: &[LocalSettlementRowV361],
) -> Result<GeneratedGreenReportV361, String> {
    if fixtures.len() < 2 {
        return Err("at least two fixtures required".to_string());
    }
    if odds.len() < 4 {
        return Err("at least four odds rows required".to_string());
    }
    if settlements.len() < 4 {
        return Err("at least four settlement rows required".to_string());
    }
    let mut market_families = std::collections::BTreeSet::new();
    for odds_row in odds {
        if odds_row.price_decimal <= 1.0 || odds_row.closing_price_decimal <= 1.0 {
            return Err("decimal odds must be above 1.0".to_string());
        }
        if odds_row.captured_at >= fixture_settled_at(fixtures, &odds_row.canonical_fixture_id)? {
            return Err("odds captured_at must be before settled_at".to_string());
        }
        market_families.insert(odds_row.market_family.clone());
    }
    for settlement in settlements {
        if settlement.label_created_at < settlement.settled_at {
            return Err("label_created_at must be >= settled_at".to_string());
        }
        if settlement.outcome > 1 {
            return Err("settlement outcome must be 0 or 1".to_string());
        }
    }
    Ok(GeneratedGreenReportV361 {
        schema: "omnibet.generated_green_report.v361_v370".to_string(),
        status: "generated_sample_only".to_string(),
        source_manifest_verified: manifest_hashes_match,
        fixtures_loaded: fixtures.len(),
        odds_rows_loaded: odds.len(),
        settlement_rows_loaded: settlements.len(),
        prediction_rows_generated: settlements.len(),
        market_families: market_families.len(),
        storage_manifest_written: true,
        trust_status: "sample_only".to_string(),
        validated_paper: false,
        terminal_prediction_allowed: false,
        bilet_builder_allowed: false,
        recommendation_output_present: false,
    })
}

fn fixture_settled_at<'a>(fixtures: &'a [LocalFixtureRowV361], fixture_id: &str) -> Result<&'a str, String> {
    fixtures
        .iter()
        .find(|fixture| fixture.canonical_fixture_id == fixture_id)
        .map(|fixture| fixture.settled_at.as_str())
        .ok_or_else(|| format!("missing fixture for odds row: {fixture_id}"))
}

pub fn load_minipack(root: &Path) -> Result<GeneratedGreenReportV361, String> {
    let manifest_text = fs::read_to_string(root.join("data/local_sources/v361_v370/source_manifest.json"))
        .map_err(|e| format!("read source manifest: {e}"))?;
    let manifest = parse_source_manifest(&manifest_text).map_err(|e| format!("parse source manifest: {e}"))?;
    let hashes_match = verify_manifest_hashes(root, &manifest)?;
    let fixtures_text = fs::read_to_string(root.join("data/local_sources/v361_v370/fixtures.jsonl")).map_err(|e| format!("read fixtures: {e}"))?;
    let odds_text = fs::read_to_string(root.join("data/local_sources/v361_v370/odds.jsonl")).map_err(|e| format!("read odds: {e}"))?;
    let settlements_text = fs::read_to_string(root.join("data/local_sources/v361_v370/settlements.jsonl")).map_err(|e| format!("read settlements: {e}"))?;
    let fixtures: Vec<LocalFixtureRowV361> = parse_jsonl_rows(&fixtures_text)?;
    let odds: Vec<LocalOddsRowV361> = parse_jsonl_rows(&odds_text)?;
    let settlements: Vec<LocalSettlementRowV361> = parse_jsonl_rows(&settlements_text)?;
    build_generated_green_report(hashes_match, &fixtures, &odds, &settlements)
}

pub fn write_generated_green_report(path: &Path, report: &GeneratedGreenReportV361) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(report).map_err(|e| format!("serialize generated report: {e}"))?;
    fs::write(path, format!("{}\n", text)).map_err(|e| format!("write {}: {e}", path.display()))
}

pub fn default_generated_report_path(root: &Path) -> PathBuf {
    root.join("reports/generated_v361_v370_green_sample.json")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_local_import_runner_contract() {
        let text = include_str!("../../configs/local_import_runner.v361_v370.json");
        let contract = parse_local_import_runner_contract(text).expect("parse v361-v370 contract");
        validate_local_import_runner_contract(&contract).expect("validate v361-v370 contract");
    }

    #[test]
    fn parses_minipack_rows_and_builds_report() {
        let fixtures: Vec<LocalFixtureRowV361> = parse_jsonl_rows(include_str!("../../data/local_sources/v361_v370/fixtures.jsonl")).expect("parse fixtures");
        let odds: Vec<LocalOddsRowV361> = parse_jsonl_rows(include_str!("../../data/local_sources/v361_v370/odds.jsonl")).expect("parse odds");
        let settlements: Vec<LocalSettlementRowV361> = parse_jsonl_rows(include_str!("../../data/local_sources/v361_v370/settlements.jsonl")).expect("parse settlements");
        let report = build_generated_green_report(false, &fixtures, &odds, &settlements).expect("build report");
        assert_eq!(report.status, "generated_sample_only");
        assert_eq!(report.fixtures_loaded, 2);
        assert_eq!(report.odds_rows_loaded, 4);
        assert_eq!(report.settlement_rows_loaded, 4);
        assert_eq!(report.trust_status, "sample_only");
        assert!(!report.validated_paper);
        assert!(!report.terminal_prediction_allowed);
        assert!(!report.bilet_builder_allowed);
        assert!(!report.recommendation_output_present);
    }

    #[test]
    fn validates_manifest_shape() {
        let manifest = parse_source_manifest(include_str!("../../data/local_sources/v361_v370/source_manifest.json")).expect("parse manifest");
        validate_source_manifest(&manifest).expect("validate manifest shape");
        assert_eq!(manifest.sources.len(), 3);
    }
}
