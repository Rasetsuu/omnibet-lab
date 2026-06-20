use crate::pack::sha256_file;
use crate::provider::{
    ApiFootballParseOutput, ProviderEventSnapshot, ProviderFixtureSnapshot,
    ProviderLineupPlayerSnapshot, ProviderMarketDiscoverySnapshot, ProviderOddsSnapshot,
    ProviderTeamStatisticSnapshot, SourceSnapshotManifest, TheOddsApiParseOutput,
};
use flate2::write::GzEncoder;
use flate2::Compression;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, File};
use std::io::{BufRead, Write};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeSnapshotCacheManifest {
    pub schema: String,
    pub cache_id: String,
    pub created_at: String,
    pub codec: String,
    pub layer: String,
    pub source_ids: Vec<String>,
    pub source_payloads: Vec<SourceSnapshotManifest>,
    pub tables: Vec<BronzeSnapshotCacheTable>,
    pub total_rows: u64,
    pub total_uncompressed_jsonl_bytes: u64,
    pub total_compressed_bytes: u64,
    pub manifest_sha256: String,
    pub credential_values_stored: bool,
    pub network_calls_performed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeSnapshotCacheTable {
    pub table: String,
    pub row_kind: String,
    pub path: String,
    pub rows: u64,
    pub uncompressed_jsonl_bytes: u64,
    pub compressed_bytes: u64,
    pub compression: String,
    pub gzip_level: u32,
    pub sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeSnapshotCacheVerifyResult {
    pub ok: bool,
    pub cache_id: String,
    pub tables_checked: usize,
    pub total_rows: u64,
    pub errors: Vec<String>,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize, PartialEq)]
pub struct BronzeSnapshotRows {
    pub source_manifests: Vec<SourceSnapshotManifest>,
    pub fixtures: Vec<ProviderFixtureSnapshot>,
    pub odds: Vec<ProviderOddsSnapshot>,
    pub market_discovery: Vec<ProviderMarketDiscoverySnapshot>,
    pub events: Vec<ProviderEventSnapshot>,
    pub lineups: Vec<ProviderLineupPlayerSnapshot>,
    pub statistics: Vec<ProviderTeamStatisticSnapshot>,
}

impl BronzeSnapshotRows {
    pub fn from_provider_samples(
        odds: &TheOddsApiParseOutput,
        football: &ApiFootballParseOutput,
    ) -> BronzeSnapshotRows {
        BronzeSnapshotRows {
            source_manifests: vec![odds.manifest.clone(), football.manifest.clone()],
            fixtures: vec![odds.fixture.clone(), football.fixture.clone()],
            odds: odds.odds.clone(),
            market_discovery: odds.markets.clone(),
            events: football.events.clone(),
            lineups: football.lineups.clone(),
            statistics: football.statistics.clone(),
        }
    }

    pub fn total_rows(&self) -> u64 {
        self.source_manifests.len() as u64
            + self.fixtures.len() as u64
            + self.odds.len() as u64
            + self.market_discovery.len() as u64
            + self.events.len() as u64
            + self.lineups.len() as u64
            + self.statistics.len() as u64
    }
}

pub fn write_bronze_snapshot_cache(
    rows: &BronzeSnapshotRows,
    out_dir: &Path,
    cache_id: &str,
    created_at: &str,
) -> Result<BronzeSnapshotCacheManifest, String> {
    if rows.total_rows() == 0 {
        return Err("bronze cache cannot be empty".to_string());
    }
    fs::create_dir_all(out_dir.join("tables"))
        .map_err(|e| format!("create bronze cache directory {}: {}", out_dir.display(), e))?;

    let mut tables = Vec::new();
    write_table(out_dir, &mut tables, "source_manifests", "source_snapshot_manifest", &rows.source_manifests)?;
    write_table(out_dir, &mut tables, "fixtures", "provider_fixture_snapshot", &rows.fixtures)?;
    write_table(out_dir, &mut tables, "odds", "provider_odds_snapshot", &rows.odds)?;
    write_table(out_dir, &mut tables, "market_discovery", "provider_market_discovery_snapshot", &rows.market_discovery)?;
    write_table(out_dir, &mut tables, "events", "provider_event_snapshot", &rows.events)?;
    write_table(out_dir, &mut tables, "lineups", "provider_lineup_player_snapshot", &rows.lineups)?;
    write_table(out_dir, &mut tables, "statistics", "provider_team_statistic_snapshot", &rows.statistics)?;

    let mut source_ids = BTreeSet::new();
    for manifest in &rows.source_manifests {
        source_ids.insert(manifest.source_id.clone());
    }

    let total_rows = tables.iter().map(|t| t.rows).sum();
    let total_uncompressed_jsonl_bytes = tables.iter().map(|t| t.uncompressed_jsonl_bytes).sum();
    let total_compressed_bytes = tables.iter().map(|t| t.compressed_bytes).sum();

    let mut manifest = BronzeSnapshotCacheManifest {
        schema: "omnibet.bronze_snapshot_cache.v236".to_string(),
        cache_id: cache_id.to_string(),
        created_at: created_at.to_string(),
        codec: "jsonl.gzip".to_string(),
        layer: "bronze_raw_provider_snapshots".to_string(),
        source_ids: source_ids.into_iter().collect(),
        source_payloads: rows.source_manifests.clone(),
        tables,
        total_rows,
        total_uncompressed_jsonl_bytes,
        total_compressed_bytes,
        manifest_sha256: String::new(),
        credential_values_stored: false,
        network_calls_performed: false,
    };
    manifest.manifest_sha256 = manifest_hash_without_self(&manifest)?;

    let manifest_path = out_dir.join("manifest.json");
    let manifest_text = serde_json::to_string_pretty(&manifest)
        .map_err(|e| format!("serialize bronze cache manifest: {}", e))?;
    fs::write(&manifest_path, format!("{}\n", manifest_text))
        .map_err(|e| format!("write bronze cache manifest {}: {}", manifest_path.display(), e))?;

    Ok(manifest)
}

pub fn load_bronze_snapshot_cache_manifest(path: &Path) -> Result<BronzeSnapshotCacheManifest, String> {
    let manifest_path = if path.is_dir() {
        path.join("manifest.json")
    } else {
        path.to_path_buf()
    };
    let file = File::open(&manifest_path)
        .map_err(|e| format!("open bronze cache manifest {}: {}", manifest_path.display(), e))?;
    serde_json::from_reader(file)
        .map_err(|e| format!("parse bronze cache manifest {}: {}", manifest_path.display(), e))
}

pub fn verify_bronze_snapshot_cache(cache_dir: &Path) -> Result<BronzeSnapshotCacheVerifyResult, String> {
    let manifest = load_bronze_snapshot_cache_manifest(cache_dir)?;
    let expected_manifest_hash = manifest_hash_without_self(&manifest)?;
    let mut errors = Vec::new();
    if manifest.schema != "omnibet.bronze_snapshot_cache.v236" {
        errors.push(format!("unexpected bronze cache schema: {}", manifest.schema));
    }
    if manifest.codec != "jsonl.gzip" {
        errors.push(format!("unexpected bronze cache codec: {}", manifest.codec));
    }
    if manifest.credential_values_stored {
        errors.push("bronze cache manifest says credential values were stored".to_string());
    }
    if manifest.network_calls_performed {
        errors.push("bronze cache manifest says network calls were performed".to_string());
    }
    if manifest.manifest_sha256 != expected_manifest_hash {
        errors.push("bronze cache manifest sha256 mismatch".to_string());
    }

    let mut total_rows = 0u64;
    for table in &manifest.tables {
        let path = cache_dir.join(&table.path);
        if !path.exists() {
            errors.push(format!("missing bronze cache table: {}", path.display()));
            continue;
        }
        let sha = sha256_file(&path)?;
        if sha != table.sha256 {
            errors.push(format!("table sha256 mismatch: {}", table.table));
        }
        let rows = count_gzip_jsonl_rows(&path)?;
        if rows != table.rows {
            errors.push(format!("table row mismatch: {} expected {} got {}", table.table, table.rows, rows));
        }
        total_rows += rows;
    }
    if total_rows != manifest.total_rows {
        errors.push(format!("total row mismatch: expected {} got {}", manifest.total_rows, total_rows));
    }

    Ok(BronzeSnapshotCacheVerifyResult {
        ok: errors.is_empty(),
        cache_id: manifest.cache_id,
        tables_checked: manifest.tables.len(),
        total_rows,
        errors,
    })
}

pub fn table_rows_as_values(cache_dir: &Path, table: &str, limit: usize) -> Result<Vec<Value>, String> {
    let manifest = load_bronze_snapshot_cache_manifest(cache_dir)?;
    let table_meta = manifest
        .tables
        .iter()
        .find(|row| row.table == table)
        .ok_or_else(|| format!("bronze cache table not found: {}", table))?;
    let path = cache_dir.join(&table_meta.path);
    let file = File::open(&path).map_err(|e| format!("open bronze cache table {}: {}", path.display(), e))?;
    let decoder = flate2::read::GzDecoder::new(file);
    let reader = std::io::BufReader::new(decoder);
    let mut rows = Vec::new();
    for line in reader.lines().take(limit) {
        let line = line.map_err(|e| format!("read bronze cache table {}: {}", path.display(), e))?;
        let row: Value = serde_json::from_str(&line)
            .map_err(|e| format!("parse bronze cache JSONL row {}: {}", path.display(), e))?;
        rows.push(row);
    }
    Ok(rows)
}

fn write_table<T: Serialize>(
    out_dir: &Path,
    tables: &mut Vec<BronzeSnapshotCacheTable>,
    table: &str,
    row_kind: &str,
    rows: &[T],
) -> Result<(), String> {
    let rel_path = format!("tables/{}.jsonl.gz", table);
    let path = out_dir.join(&rel_path);
    let mut uncompressed = Vec::new();
    for row in rows {
        serde_json::to_writer(&mut uncompressed, row)
            .map_err(|e| format!("serialize row for {}: {}", table, e))?;
        uncompressed.push(b'\n');
    }

    let file = File::create(&path)
        .map_err(|e| format!("create bronze cache table {}: {}", path.display(), e))?;
    let mut encoder = GzEncoder::new(file, Compression::new(6));
    encoder
        .write_all(&uncompressed)
        .map_err(|e| format!("write gzip table {}: {}", path.display(), e))?;
    encoder
        .finish()
        .map_err(|e| format!("finish gzip table {}: {}", path.display(), e))?;

    let compressed_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);
    let sha256 = sha256_file(&path)?;
    tables.push(BronzeSnapshotCacheTable {
        table: table.to_string(),
        row_kind: row_kind.to_string(),
        path: rel_path,
        rows: rows.len() as u64,
        uncompressed_jsonl_bytes: uncompressed.len() as u64,
        compressed_bytes,
        compression: "gzip".to_string(),
        gzip_level: 6,
        sha256,
    });
    Ok(())
}

fn manifest_hash_without_self(manifest: &BronzeSnapshotCacheManifest) -> Result<String, String> {
    let mut clone = manifest.clone();
    clone.manifest_sha256.clear();
    let text = serde_json::to_string(&clone).map_err(|e| format!("serialize manifest for hash: {}", e))?;
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    Ok(format!("{:x}", hasher.finalize()))
}

fn count_gzip_jsonl_rows(path: &Path) -> Result<u64, String> {
    let file = File::open(path).map_err(|e| format!("open gzip jsonl {}: {}", path.display(), e))?;
    let decoder = flate2::read::GzDecoder::new(file);
    let reader = std::io::BufReader::new(decoder);
    let mut count = 0u64;
    for line in reader.lines() {
        line.map_err(|e| format!("read gzip jsonl {}: {}", path.display(), e))?;
        count += 1;
    }
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provider::{parse_api_football_live_state_sample, parse_the_odds_api_event_markets_sample};

    #[test]
    fn writes_and_verifies_offline_bronze_cache() {
        let odds = parse_the_odds_api_event_markets_sample(
            include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
            "2026-06-16T18:02:00Z",
        )
        .expect("parse odds sample");
        let football = parse_api_football_live_state_sample(
            include_str!("../../data/samples/api_football_live_state_sample.json"),
            "2026-06-16T22:00:00Z",
        )
        .expect("parse football sample");
        let rows = BronzeSnapshotRows::from_provider_samples(&odds, &football);
        assert_eq!(rows.total_rows(), 53);

        let out_dir = std::env::temp_dir().join("omnibet_v236_bronze_cache_test");
        if out_dir.exists() {
            fs::remove_dir_all(&out_dir).expect("clean stale test dir");
        }
        let manifest = write_bronze_snapshot_cache(
            &rows,
            &out_dir,
            "v236_test_cache",
            "2026-06-20T00:00:00Z",
        )
        .expect("write bronze cache");
        assert_eq!(manifest.schema, "omnibet.bronze_snapshot_cache.v236");
        assert_eq!(manifest.total_rows, 53);
        assert_eq!(manifest.tables.len(), 7);
        assert!(!manifest.credential_values_stored);
        assert!(!manifest.network_calls_performed);
        assert!(manifest.source_ids.contains(&"the_odds_api".to_string()));
        assert!(manifest.source_ids.contains(&"api_football".to_string()));

        let verify = verify_bronze_snapshot_cache(&out_dir).expect("verify bronze cache");
        assert!(verify.ok, "{:?}", verify.errors);
        assert_eq!(verify.total_rows, 53);

        let market_rows = table_rows_as_values(&out_dir, "market_discovery", 20)
            .expect("read market discovery rows");
        assert!(market_rows.iter().any(|row| {
            row.get("market_key").and_then(Value::as_str) == Some("special_combo_unknown")
                && row.get("needs_mapping_review").and_then(Value::as_bool) == Some(true)
        }));

        fs::remove_dir_all(&out_dir).expect("clean test dir");
    }
}
