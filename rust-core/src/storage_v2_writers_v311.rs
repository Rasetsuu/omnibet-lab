use flate2::write::GzEncoder;
use flate2::Compression;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufRead, Read, Write};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2TableManifestV311 {
    pub schema: String,
    pub writer_id: String,
    pub layer: String,
    pub table: String,
    pub codec: String,
    pub relative_path: String,
    pub row_count: u64,
    pub uncompressed_bytes: u64,
    pub compressed_bytes: u64,
    pub content_sha256: String,
    pub created_at: String,
    pub credential_values_stored: bool,
    pub network_calls_performed: bool,
    pub retention_policy: String,
    pub promotion_state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2BundleManifestV311 {
    pub schema: String,
    pub bundle_id: String,
    pub created_at: String,
    pub tables: Vec<StorageV2TableManifestV311>,
    pub total_rows: u64,
    pub total_uncompressed_bytes: u64,
    pub total_compressed_bytes: u64,
    pub bundle_sha256: String,
    pub credential_values_stored: bool,
    pub network_calls_performed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StorageV2WriterVerifyResultV311 {
    pub ok: bool,
    pub tables_checked: usize,
    pub total_rows: u64,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RetentionGateDecisionV311 {
    pub can_delete: bool,
    pub reason: String,
}

pub fn parse_storage_v2_writers_contract(text: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(text)
}

fn string_array_contains(value: &Value, key: &str, expected: &str) -> bool {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|items| items.iter().any(|item| item.as_str() == Some(expected)))
        .unwrap_or(false)
}

fn require_string_array(value: &Value, key: &str, required: &[&str]) -> Result<(), String> {
    for item in required {
        if !string_array_contains(value, key, item) {
            return Err(format!("{key} missing required item: {item}"));
        }
    }
    Ok(())
}

pub fn validate_storage_v2_writers_contract(contract: &Value) -> Result<(), String> {
    if contract.get("schema").and_then(Value::as_str)
        != Some("omnibet.storage_v2_writers_contract.v311_v320")
    {
        return Err("unexpected v311-v320 storage writers schema".to_string());
    }
    for flag in ["paper_only", "local_first"] {
        if contract.get(flag).and_then(Value::as_bool) != Some(true) {
            return Err(format!("{flag} must be true"));
        }
    }
    for flag in [
        "live_provider_calls_allowed",
        "credential_values_allowed",
        "real_money_recommendations_allowed",
    ] {
        if contract.get(flag).and_then(Value::as_bool) != Some(false) {
            return Err(format!("{flag} must be false"));
        }
    }
    require_string_array(contract, "allowed_codecs", &["jsonl.zstd", "json.zstd", "jsonl.gzip", "parquet.zstd"])?;
    require_string_array(contract, "implemented_codecs_now", &["jsonl.zstd", "json.zstd", "jsonl.gzip"])?;
    require_string_array(contract, "manifest_only_codecs_now", &["parquet.zstd"])?;
    require_string_array(
        contract,
        "required_manifest_fields",
        &[
            "writer_id",
            "layer",
            "table",
            "codec",
            "relative_path",
            "row_count",
            "uncompressed_bytes",
            "compressed_bytes",
            "content_sha256",
            "retention_policy",
            "promotion_state",
        ],
    )?;
    let targets = contract
        .get("writer_targets")
        .and_then(Value::as_array)
        .ok_or_else(|| "writer_targets missing".to_string())?;
    for required_writer in [
        "bronze_raw_jsonl_zstd_writer",
        "bronze_raw_json_zstd_writer",
        "silver_parquet_zstd_manifest_writer",
        "gold_parquet_zstd_manifest_writer",
        "ci_runtime_jsonl_gzip_writer",
    ] {
        if !targets.iter().any(|row| row.get("writer_id").and_then(Value::as_str) == Some(required_writer)) {
            return Err(format!("missing writer target: {required_writer}"));
        }
    }
    let retention = contract
        .get("retention_gates")
        .and_then(Value::as_object)
        .ok_or_else(|| "retention_gates missing".to_string())?;
    if retention.get("delete_requires_content_hash_match").and_then(Value::as_bool) != Some(true)
        || retention.get("delete_requires_row_count_match").and_then(Value::as_bool) != Some(true)
        || retention.get("delete_requires_promotion_state").and_then(Value::as_str) != Some("verified_promoted")
    {
        return Err("retention gates must require hash, rows, and verified promotion".to_string());
    }
    let acceptance = contract
        .get("acceptance")
        .and_then(Value::as_object)
        .ok_or_else(|| "acceptance missing".to_string())?;
    for (key, value) in acceptance.iter() {
        if value.as_bool() != Some(true) {
            return Err(format!("acceptance gate not enabled: {key}"));
        }
    }
    Ok(())
}

pub fn write_jsonl_zstd_table(
    out_dir: &Path,
    table: &str,
    rows: &[Value],
    created_at: &str,
) -> Result<StorageV2TableManifestV311, String> {
    let rel_path = format!("bronze/{table}.jsonl.zst");
    let path = out_dir.join(&rel_path);
    write_compressed_jsonl(out_dir, &path, rows, Codec::JsonlZstd)?;
    table_manifest(
        "bronze_raw_jsonl_zstd_writer",
        "bronze_raw_snapshots",
        table,
        "jsonl.zstd",
        &rel_path,
        rows,
        &path,
        created_at,
        "temporary_delete_after_verified_promotion",
        "preview_only",
    )
}

pub fn write_json_zstd_payload(
    out_dir: &Path,
    table: &str,
    payload: &Value,
    created_at: &str,
) -> Result<StorageV2TableManifestV311, String> {
    let rel_path = format!("bronze/{table}.json.zst");
    let path = out_dir.join(&rel_path);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_vec(payload).map_err(|e| format!("serialize json payload: {e}"))?;
    let file = File::create(&path).map_err(|e| format!("create {}: {e}", path.display()))?;
    let mut encoder = zstd::stream::write::Encoder::new(file, 3)
        .map_err(|e| format!("create zstd encoder {}: {e}", path.display()))?;
    encoder
        .write_all(&text)
        .map_err(|e| format!("write zstd payload {}: {e}", path.display()))?;
    encoder
        .finish()
        .map_err(|e| format!("finish zstd payload {}: {e}", path.display()))?;
    let compressed_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);
    Ok(StorageV2TableManifestV311 {
        schema: "omnibet.storage_v2_table_manifest.v311".to_string(),
        writer_id: "bronze_raw_json_zstd_writer".to_string(),
        layer: "bronze_raw_payloads".to_string(),
        table: table.to_string(),
        codec: "json.zstd".to_string(),
        relative_path: rel_path,
        row_count: 1,
        uncompressed_bytes: text.len() as u64,
        compressed_bytes,
        content_sha256: sha256_file(&path)?,
        created_at: created_at.to_string(),
        credential_values_stored: false,
        network_calls_performed: false,
        retention_policy: "temporary_delete_after_verified_promotion".to_string(),
        promotion_state: "preview_only".to_string(),
    })
}

pub fn write_jsonl_gzip_table(
    out_dir: &Path,
    table: &str,
    rows: &[Value],
    created_at: &str,
) -> Result<StorageV2TableManifestV311, String> {
    let rel_path = format!("runtime/{table}.jsonl.gz");
    let path = out_dir.join(&rel_path);
    write_compressed_jsonl(out_dir, &path, rows, Codec::JsonlGzip)?;
    table_manifest(
        "ci_runtime_jsonl_gzip_writer",
        "ci_runtime_packs",
        table,
        "jsonl.gzip",
        &rel_path,
        rows,
        &path,
        created_at,
        "small_pack_keep",
        "preview_only",
    )
}

pub fn build_parquet_zstd_manifest_only(
    writer_id: &str,
    layer: &str,
    table: &str,
    row_count: u64,
    created_at: &str,
) -> StorageV2TableManifestV311 {
    StorageV2TableManifestV311 {
        schema: "omnibet.storage_v2_table_manifest.v311".to_string(),
        writer_id: writer_id.to_string(),
        layer: layer.to_string(),
        table: table.to_string(),
        codec: "parquet.zstd".to_string(),
        relative_path: format!("{layer}/{table}.parquet"),
        row_count,
        uncompressed_bytes: 0,
        compressed_bytes: 0,
        content_sha256: "manifest_only_pending_real_parquet_writer".to_string(),
        created_at: created_at.to_string(),
        credential_values_stored: false,
        network_calls_performed: false,
        retention_policy: "long_term_keep".to_string(),
        promotion_state: "manifest_only".to_string(),
    }
}

pub fn build_bundle_manifest(
    bundle_id: &str,
    created_at: &str,
    tables: Vec<StorageV2TableManifestV311>,
) -> Result<StorageV2BundleManifestV311, String> {
    if tables.is_empty() {
        return Err("storage writer bundle cannot be empty".to_string());
    }
    let total_rows = tables.iter().map(|row| row.row_count).sum();
    let total_uncompressed_bytes = tables.iter().map(|row| row.uncompressed_bytes).sum();
    let total_compressed_bytes = tables.iter().map(|row| row.compressed_bytes).sum();
    let mut manifest = StorageV2BundleManifestV311 {
        schema: "omnibet.storage_v2_bundle_manifest.v311".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        tables,
        total_rows,
        total_uncompressed_bytes,
        total_compressed_bytes,
        bundle_sha256: String::new(),
        credential_values_stored: false,
        network_calls_performed: false,
    };
    manifest.bundle_sha256 = bundle_hash_without_self(&manifest)?;
    Ok(manifest)
}

pub fn verify_storage_writer_bundle(
    out_dir: &Path,
    manifest: &StorageV2BundleManifestV311,
) -> Result<StorageV2WriterVerifyResultV311, String> {
    let mut errors = Vec::new();
    if manifest.credential_values_stored {
        errors.push("bundle manifest says credential values were stored".to_string());
    }
    if manifest.network_calls_performed {
        errors.push("bundle manifest says network calls were performed".to_string());
    }
    if manifest.bundle_sha256 != bundle_hash_without_self(manifest)? {
        errors.push("bundle manifest sha256 mismatch".to_string());
    }
    let mut total_rows = 0u64;
    for table in &manifest.tables {
        if table.codec == "parquet.zstd" && table.promotion_state == "manifest_only" {
            total_rows += table.row_count;
            continue;
        }
        let path = out_dir.join(&table.relative_path);
        if !path.exists() {
            errors.push(format!("missing table file: {}", path.display()));
            continue;
        }
        let sha = sha256_file(&path)?;
        if sha != table.content_sha256 {
            errors.push(format!("content sha mismatch: {}", table.table));
        }
        let rows = match table.codec.as_str() {
            "jsonl.zstd" => count_zstd_jsonl_rows(&path)?,
            "jsonl.gzip" => count_gzip_jsonl_rows(&path)?,
            "json.zstd" => 1,
            other => {
                errors.push(format!("unsupported verification codec: {other}"));
                0
            }
        };
        if rows != table.row_count {
            errors.push(format!("row count mismatch for {}: expected {} got {}", table.table, table.row_count, rows));
        }
        total_rows += rows;
    }
    if total_rows != manifest.total_rows {
        errors.push(format!("bundle total row mismatch: expected {} got {}", manifest.total_rows, total_rows));
    }
    Ok(StorageV2WriterVerifyResultV311 {
        ok: errors.is_empty(),
        tables_checked: manifest.tables.len(),
        total_rows,
        errors,
    })
}

pub fn retention_gate_decision(
    manifest: &StorageV2TableManifestV311,
    content_hash_matches: bool,
    row_count_matches: bool,
) -> RetentionGateDecisionV311 {
    if manifest.retention_policy != "temporary_delete_after_verified_promotion" {
        return RetentionGateDecisionV311 {
            can_delete: false,
            reason: "retention_policy_is_not_temporary".to_string(),
        };
    }
    if !content_hash_matches {
        return RetentionGateDecisionV311 {
            can_delete: false,
            reason: "content_hash_mismatch".to_string(),
        };
    }
    if !row_count_matches {
        return RetentionGateDecisionV311 {
            can_delete: false,
            reason: "row_count_mismatch".to_string(),
        };
    }
    if manifest.promotion_state != "verified_promoted" {
        return RetentionGateDecisionV311 {
            can_delete: false,
            reason: "promotion_state_not_verified_promoted".to_string(),
        };
    }
    RetentionGateDecisionV311 {
        can_delete: true,
        reason: "verified_promoted_with_matching_hash_and_rows".to_string(),
    }
}

enum Codec {
    JsonlZstd,
    JsonlGzip,
}

fn write_compressed_jsonl(
    out_dir: &Path,
    path: &Path,
    rows: &[Value],
    codec: Codec,
) -> Result<(), String> {
    if rows.is_empty() {
        return Err("storage writer table cannot be empty".to_string());
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    } else {
        fs::create_dir_all(out_dir).map_err(|e| format!("create {}: {e}", out_dir.display()))?;
    }
    let mut uncompressed = Vec::new();
    for row in rows {
        serde_json::to_writer(&mut uncompressed, row)
            .map_err(|e| format!("serialize jsonl row: {e}"))?;
        uncompressed.push(b'\n');
    }
    match codec {
        Codec::JsonlZstd => {
            let file = File::create(path).map_err(|e| format!("create {}: {e}", path.display()))?;
            let mut encoder = zstd::stream::write::Encoder::new(file, 3)
                .map_err(|e| format!("create zstd encoder {}: {e}", path.display()))?;
            encoder
                .write_all(&uncompressed)
                .map_err(|e| format!("write zstd table {}: {e}", path.display()))?;
            encoder
                .finish()
                .map_err(|e| format!("finish zstd table {}: {e}", path.display()))?;
        }
        Codec::JsonlGzip => {
            let file = File::create(path).map_err(|e| format!("create {}: {e}", path.display()))?;
            let mut encoder = GzEncoder::new(file, Compression::new(6));
            encoder
                .write_all(&uncompressed)
                .map_err(|e| format!("write gzip table {}: {e}", path.display()))?;
            encoder
                .finish()
                .map_err(|e| format!("finish gzip table {}: {e}", path.display()))?;
        }
    }
    Ok(())
}

fn table_manifest(
    writer_id: &str,
    layer: &str,
    table: &str,
    codec: &str,
    rel_path: &str,
    rows: &[Value],
    path: &Path,
    created_at: &str,
    retention_policy: &str,
    promotion_state: &str,
) -> Result<StorageV2TableManifestV311, String> {
    let mut uncompressed = Vec::new();
    for row in rows {
        serde_json::to_writer(&mut uncompressed, row)
            .map_err(|e| format!("serialize row for manifest: {e}"))?;
        uncompressed.push(b'\n');
    }
    let compressed_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);
    Ok(StorageV2TableManifestV311 {
        schema: "omnibet.storage_v2_table_manifest.v311".to_string(),
        writer_id: writer_id.to_string(),
        layer: layer.to_string(),
        table: table.to_string(),
        codec: codec.to_string(),
        relative_path: rel_path.to_string(),
        row_count: rows.len() as u64,
        uncompressed_bytes: uncompressed.len() as u64,
        compressed_bytes,
        content_sha256: sha256_file(path)?,
        created_at: created_at.to_string(),
        credential_values_stored: false,
        network_calls_performed: false,
        retention_policy: retention_policy.to_string(),
        promotion_state: promotion_state.to_string(),
    })
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file = File::open(path).map_err(|e| format!("open {}: {e}", path.display()))?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 8192];
    loop {
        let n = file.read(&mut buf).map_err(|e| format!("read {}: {e}", path.display()))?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

fn bundle_hash_without_self(manifest: &StorageV2BundleManifestV311) -> Result<String, String> {
    let mut clone = manifest.clone();
    clone.bundle_sha256.clear();
    let text = serde_json::to_string(&clone).map_err(|e| format!("serialize bundle manifest: {e}"))?;
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    Ok(format!("{:x}", hasher.finalize()))
}

fn count_zstd_jsonl_rows(path: &Path) -> Result<u64, String> {
    let file = File::open(path).map_err(|e| format!("open zstd jsonl {}: {e}", path.display()))?;
    let decoder = zstd::stream::read::Decoder::new(file)
        .map_err(|e| format!("create zstd decoder {}: {e}", path.display()))?;
    count_jsonl_rows_from_reader(decoder, path)
}

fn count_gzip_jsonl_rows(path: &Path) -> Result<u64, String> {
    let file = File::open(path).map_err(|e| format!("open gzip jsonl {}: {e}", path.display()))?;
    let decoder = flate2::read::GzDecoder::new(file);
    count_jsonl_rows_from_reader(decoder, path)
}

fn count_jsonl_rows_from_reader<R: Read>(reader: R, path: &Path) -> Result<u64, String> {
    let reader = std::io::BufReader::new(reader);
    let mut count = 0u64;
    for line in reader.lines() {
        line.map_err(|e| format!("read jsonl {}: {e}", path.display()))?;
        count += 1;
    }
    Ok(count)
}

pub fn sample_rows() -> Vec<Value> {
    vec![
        serde_json::json!({"canonical_fixture_id":"canonical:fixture:ars-che:2026-06-28","market_key":"1x2","selection_key":"home","price_decimal":2.05}),
        serde_json::json!({"canonical_fixture_id":"canonical:fixture:ars-che:2026-06-28","market_key":"totals","selection_key":"over_2_5","price_decimal":1.91}),
        serde_json::json!({"canonical_fixture_id":"canonical:fixture:inter-milan:2026-06-27","market_key":"1x2","selection_key":"home","price_decimal":2.05}),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_storage_v2_writers_contract() {
        let text = include_str!("../../configs/storage_v2_writers.v311_v320.json");
        let contract = parse_storage_v2_writers_contract(text).expect("parse v311-v320 contract");
        validate_storage_v2_writers_contract(&contract).expect("validate v311-v320 contract");
    }

    #[test]
    fn writes_and_verifies_storage_writer_bundle() {
        let rows = sample_rows();
        let out_dir: PathBuf = std::env::temp_dir().join("omnibet_v311_storage_writer_test");
        if out_dir.exists() {
            fs::remove_dir_all(&out_dir).expect("clean stale storage writer test dir");
        }
        let created_at = "2026-06-27T00:00:00Z";
        let zstd_manifest = write_jsonl_zstd_table(&out_dir, "provider_odds_snapshot_preview", &rows, created_at)
            .expect("write jsonl zstd table");
        let gzip_manifest = write_jsonl_gzip_table(&out_dir, "small_runtime_pack_preview", &rows[..2], created_at)
            .expect("write jsonl gzip table");
        let json_manifest = write_json_zstd_payload(
            &out_dir,
            "raw_payload_preview",
            &serde_json::json!({"payload":"sample","rows":rows.len()}),
            created_at,
        )
        .expect("write json zstd payload");
        let silver_manifest = build_parquet_zstd_manifest_only(
            "silver_parquet_zstd_manifest_writer",
            "silver_canonical_facts",
            "silver_fixture_facts_preview",
            2,
            created_at,
        );
        let gold_manifest = build_parquet_zstd_manifest_only(
            "gold_parquet_zstd_manifest_writer",
            "gold_training_features",
            "gold_market_features_preview",
            2,
            created_at,
        );
        assert_eq!(zstd_manifest.codec, "jsonl.zstd");
        assert_eq!(gzip_manifest.codec, "jsonl.gzip");
        assert_eq!(json_manifest.codec, "json.zstd");
        assert_eq!(silver_manifest.codec, "parquet.zstd");
        assert_eq!(gold_manifest.codec, "parquet.zstd");
        assert!(!zstd_manifest.credential_values_stored);
        assert!(!zstd_manifest.network_calls_performed);

        let bundle = build_bundle_manifest(
            "v311_storage_writer_bundle_test",
            created_at,
            vec![zstd_manifest.clone(), gzip_manifest, json_manifest, silver_manifest, gold_manifest],
        )
        .expect("build storage writer bundle");
        let verify = verify_storage_writer_bundle(&out_dir, &bundle).expect("verify storage writer bundle");
        assert!(verify.ok, "{:?}", verify.errors);
        assert_eq!(verify.total_rows, bundle.total_rows);

        let not_delete = retention_gate_decision(&zstd_manifest, true, true);
        assert!(!not_delete.can_delete);
        assert_eq!(not_delete.reason, "promotion_state_not_verified_promoted");
        let mut promoted = zstd_manifest.clone();
        promoted.promotion_state = "verified_promoted".to_string();
        let can_delete = retention_gate_decision(&promoted, true, true);
        assert!(can_delete.can_delete);

        fs::remove_dir_all(&out_dir).expect("clean storage writer test dir");
    }
}
