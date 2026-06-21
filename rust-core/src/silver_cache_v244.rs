use crate::pack::sha256_file;
use crate::{build_silver_fact_preview_bundle_from_offline_samples, SilverFactPreviewBundle, SilverFactPreviewRow};
use flate2::write::GzEncoder;
use flate2::Compression;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufRead, Write};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverPreviewCacheManifest {
    pub schema: String,
    pub cache_id: String,
    pub created_at: String,
    pub codec: String,
    pub layer: String,
    pub source_bundle_id: String,
    pub tables: Vec<SilverPreviewCacheTable>,
    pub total_rows: u64,
    pub total_uncompressed_jsonl_bytes: u64,
    pub total_compressed_bytes: u64,
    pub manifest_sha256: String,
    pub preview_only: bool,
    pub training_dataset_promotion_allowed: bool,
    pub credential_values_stored: bool,
    pub network_calls_performed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SilverPreviewCacheTable {
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
pub struct SilverPreviewCacheVerifyResult {
    pub ok: bool,
    pub cache_id: String,
    pub tables_checked: usize,
    pub total_rows: u64,
    pub errors: Vec<String>,
}

pub fn write_silver_preview_cache(
    bundle: &SilverFactPreviewBundle,
    out_dir: &Path,
    cache_id: &str,
    created_at: &str,
) -> Result<SilverPreviewCacheManifest, String> {
    if !bundle.preview_only || bundle.training_dataset_promotion_allowed {
        return Err("silver preview cache requires preview-only non-training bundle".to_string());
    }
    if bundle.total_rows == 0 || bundle.rows.is_empty() {
        return Err("silver preview cache cannot be empty".to_string());
    }
    fs::create_dir_all(out_dir.join("tables"))
        .map_err(|e| format!("create silver preview cache directory {}: {}", out_dir.display(), e))?;

    let mut tables = Vec::new();
    write_table(out_dir, &mut tables, "silver_fact_preview_rows", "silver_fact_preview_row", &bundle.rows)?;

    let total_rows = tables.iter().map(|row| row.rows).sum();
    let total_uncompressed_jsonl_bytes = tables.iter().map(|row| row.uncompressed_jsonl_bytes).sum();
    let total_compressed_bytes = tables.iter().map(|row| row.compressed_bytes).sum();
    let mut manifest = SilverPreviewCacheManifest {
        schema: "omnibet.silver_preview_cache.v244".to_string(),
        cache_id: cache_id.to_string(),
        created_at: created_at.to_string(),
        codec: "jsonl.gzip".to_string(),
        layer: "silver_fact_preview".to_string(),
        source_bundle_id: bundle.bundle_id.clone(),
        tables,
        total_rows,
        total_uncompressed_jsonl_bytes,
        total_compressed_bytes,
        manifest_sha256: String::new(),
        preview_only: true,
        training_dataset_promotion_allowed: false,
        credential_values_stored: false,
        network_calls_performed: false,
    };
    manifest.manifest_sha256 = manifest_hash_without_self(&manifest)?;
    let manifest_text = serde_json::to_string_pretty(&manifest)
        .map_err(|e| format!("serialize silver preview manifest: {}", e))?;
    let manifest_path = out_dir.join("manifest.json");
    fs::write(&manifest_path, format!("{}\n", manifest_text))
        .map_err(|e| format!("write silver preview manifest {}: {}", manifest_path.display(), e))?;
    Ok(manifest)
}

pub fn load_silver_preview_cache_manifest(path: &Path) -> Result<SilverPreviewCacheManifest, String> {
    let manifest_path = if path.is_dir() { path.join("manifest.json") } else { path.to_path_buf() };
    let file = File::open(&manifest_path)
        .map_err(|e| format!("open silver preview manifest {}: {}", manifest_path.display(), e))?;
    serde_json::from_reader(file)
        .map_err(|e| format!("parse silver preview manifest {}: {}", manifest_path.display(), e))
}

pub fn verify_silver_preview_cache(cache_dir: &Path) -> Result<SilverPreviewCacheVerifyResult, String> {
    let manifest = load_silver_preview_cache_manifest(cache_dir)?;
    let expected_manifest_hash = manifest_hash_without_self(&manifest)?;
    let mut errors = Vec::new();
    if manifest.schema != "omnibet.silver_preview_cache.v244" {
        errors.push(format!("unexpected silver preview cache schema: {}", manifest.schema));
    }
    if manifest.codec != "jsonl.gzip" {
        errors.push(format!("unexpected silver preview cache codec: {}", manifest.codec));
    }
    if !manifest.preview_only || manifest.training_dataset_promotion_allowed {
        errors.push("silver preview cache training/preview flags are unsafe".to_string());
    }
    if manifest.credential_values_stored {
        errors.push("silver preview cache manifest says credential values were stored".to_string());
    }
    if manifest.network_calls_performed {
        errors.push("silver preview cache manifest says network calls were performed".to_string());
    }
    if manifest.manifest_sha256 != expected_manifest_hash {
        errors.push("silver preview cache manifest sha256 mismatch".to_string());
    }
    let mut total_rows = 0u64;
    for table in &manifest.tables {
        let path = cache_dir.join(&table.path);
        if !path.exists() {
            errors.push(format!("missing silver preview table: {}", path.display()));
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
    Ok(SilverPreviewCacheVerifyResult {
        ok: errors.is_empty(),
        cache_id: manifest.cache_id,
        tables_checked: manifest.tables.len(),
        total_rows,
        errors,
    })
}

pub fn write_silver_preview_cache_from_offline_samples(
    out_dir: &Path,
    cache_id: &str,
    created_at: &str,
) -> Result<SilverPreviewCacheManifest, String> {
    let bundle = build_silver_fact_preview_bundle_from_offline_samples(
        include_str!("../../configs/market_registry.v237.json"),
        include_str!("../../configs/market_review_patch.v242.json"),
        include_str!("../../configs/identity_mapping_preview.v239.json"),
        include_str!("../../data/samples/the_odds_api_event_markets_sample.json"),
        include_str!("../../data/samples/api_football_live_state_sample.json"),
        created_at,
    )?;
    write_silver_preview_cache(&bundle, out_dir, cache_id, created_at)
}

fn write_table<T: Serialize>(
    out_dir: &Path,
    tables: &mut Vec<SilverPreviewCacheTable>,
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
        .map_err(|e| format!("create silver preview table {}: {}", path.display(), e))?;
    let mut encoder = GzEncoder::new(file, Compression::new(6));
    encoder
        .write_all(&uncompressed)
        .map_err(|e| format!("write gzip table {}: {}", path.display(), e))?;
    encoder
        .finish()
        .map_err(|e| format!("finish gzip table {}: {}", path.display(), e))?;
    let compressed_bytes = path.metadata().map(|meta| meta.len()).unwrap_or(0);
    let sha256 = sha256_file(&path)?;
    tables.push(SilverPreviewCacheTable {
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

fn manifest_hash_without_self(manifest: &SilverPreviewCacheManifest) -> Result<String, String> {
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

pub fn silver_preview_rows_as_values(cache_dir: &Path, limit: usize) -> Result<Vec<serde_json::Value>, String> {
    let manifest = load_silver_preview_cache_manifest(cache_dir)?;
    let table = manifest
        .tables
        .iter()
        .find(|row| row.table == "silver_fact_preview_rows")
        .ok_or_else(|| "silver fact preview table not found".to_string())?;
    let path = cache_dir.join(&table.path);
    let file = File::open(&path).map_err(|e| format!("open silver preview table {}: {}", path.display(), e))?;
    let decoder = flate2::read::GzDecoder::new(file);
    let reader = std::io::BufReader::new(decoder);
    let mut rows = Vec::new();
    for line in reader.lines().take(limit) {
        let line = line.map_err(|e| format!("read silver preview table {}: {}", path.display(), e))?;
        let row: serde_json::Value = serde_json::from_str(&line)
            .map_err(|e| format!("parse silver preview JSONL row {}: {}", path.display(), e))?;
        rows.push(row);
    }
    Ok(rows)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writes_and_verifies_silver_preview_cache() {
        let out_dir = std::env::temp_dir().join("omnibet_v244_silver_preview_cache_test");
        if out_dir.exists() {
            fs::remove_dir_all(&out_dir).expect("clean stale silver preview cache test dir");
        }
        let manifest = write_silver_preview_cache_from_offline_samples(
            &out_dir,
            "v244_test_silver_preview_cache",
            "2026-06-20T00:00:00Z",
        )
        .expect("write silver preview cache");
        assert_eq!(manifest.schema, "omnibet.silver_preview_cache.v244");
        assert_eq!(manifest.total_rows, 22);
        assert_eq!(manifest.tables.len(), 1);
        assert!(manifest.preview_only);
        assert!(!manifest.training_dataset_promotion_allowed);
        assert!(!manifest.credential_values_stored);
        assert!(!manifest.network_calls_performed);

        let verify = verify_silver_preview_cache(&out_dir).expect("verify silver preview cache");
        assert!(verify.ok, "{:?}", verify.errors);
        assert_eq!(verify.total_rows, 22);
        let rows = silver_preview_rows_as_values(&out_dir, 30).expect("read preview rows");
        assert_eq!(rows.len(), 22);
        assert!(rows.iter().any(|row| {
            row.get("provider_key").and_then(serde_json::Value::as_str) == Some("special_combo_unknown")
                && row.get("training_dataset_promotion_allowed").and_then(serde_json::Value::as_bool) == Some(false)
        }));
        fs::remove_dir_all(&out_dir).expect("clean silver preview cache test dir");
    }
}
