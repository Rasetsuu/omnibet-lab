use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackColumn {
    pub cid: Option<i64>,
    pub name: String,
    #[serde(rename = "type")]
    pub col_type: Option<String>,
    pub notnull: Option<bool>,
    pub default: Option<Value>,
    pub pk: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackTable {
    pub table: String,
    pub path: String,
    pub rows: u64,
    pub uncompressed_jsonl_bytes: Option<u64>,
    pub compressed_bytes: u64,
    pub compression: String,
    pub gzip_level: Option<u8>,
    pub compression_ratio: Option<f64>,
    pub sha256: String,
    pub schema: Vec<PackColumn>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoragePolicy {
    pub current_codec: Option<String>,
    pub future_preferred_codec: Option<String>,
    pub sqlite_role: Option<String>,
    pub pack_role: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataPackManifest {
    pub pack_name: String,
    pub sport: String,
    pub created_at: Option<String>,
    pub source_db: Option<String>,
    pub format: String,
    pub storage_policy: Option<StoragePolicy>,
    pub tables: Vec<PackTable>,
    pub skipped: Option<Vec<Value>>,
    pub total_rows: Option<u64>,
    pub total_uncompressed_jsonl_bytes: Option<u64>,
    pub total_compressed_bytes: Option<u64>,
    pub overall_compression_ratio: Option<f64>,
    pub manifest_sha256: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct TableVerifyResult {
    pub table: String,
    pub file_path: String,
    pub expected_rows: u64,
    pub actual_rows: u64,
    pub expected_sha256: String,
    pub actual_sha256: String,
    pub rows_ok: bool,
    pub sha_ok: bool,
    pub compressed_bytes: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct PackVerifyResult {
    pub ok: bool,
    pub pack_name: String,
    pub sport: String,
    pub tables_checked: usize,
    pub total_rows: u64,
    pub total_compressed_bytes: u64,
    pub results: Vec<TableVerifyResult>,
    pub errors: Vec<String>,
}

pub fn load_manifest(pack_dir: &Path) -> Result<DataPackManifest, String> {
    let manifest_path = pack_dir.join("manifest.json");
    let file = File::open(&manifest_path)
        .map_err(|e| format!("failed to open manifest {}: {}", manifest_path.display(), e))?;
    serde_json::from_reader(file)
        .map_err(|e| format!("failed to parse manifest {}: {}", manifest_path.display(), e))
}

fn resolve_table_path(pack_dir: &Path, table: &PackTable) -> PathBuf {
    let p = PathBuf::from(&table.path);
    if p.exists() {
        return p;
    }
    if p.is_relative() {
        let rel = pack_dir.join(&p);
        if rel.exists() {
            return rel;
        }
    }
    pack_dir.join("tables").join(format!("{}.jsonl.gz", table.table))
}

pub fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file = File::open(path)
        .map_err(|e| format!("failed to open {} for sha256: {}", path.display(), e))?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let n = file
            .read(&mut buf)
            .map_err(|e| format!("failed to read {} for sha256: {}", path.display(), e))?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

pub fn count_gzip_jsonl_rows(path: &Path) -> Result<u64, String> {
    let file = File::open(path)
        .map_err(|e| format!("failed to open gzip table {}: {}", path.display(), e))?;
    let decoder = GzDecoder::new(file);
    let reader = BufReader::new(decoder);
    let mut rows = 0u64;
    for line in reader.lines() {
        line.map_err(|e| format!("failed reading gzip jsonl {}: {}", path.display(), e))?;
        rows += 1;
    }
    Ok(rows)
}

pub fn verify_pack(pack_dir: &Path) -> Result<PackVerifyResult, String> {
    let manifest = load_manifest(pack_dir)?;
    let mut results = Vec::new();
    let mut errors = Vec::new();
    let mut total_rows = 0u64;
    let mut total_compressed_bytes = 0u64;

    for table in &manifest.tables {
        if table.compression.to_lowercase() != "gzip" {
            errors.push(format!(
                "unsupported compression for table {}: {}",
                table.table, table.compression
            ));
            continue;
        }

        let path = resolve_table_path(pack_dir, table);
        if !path.exists() {
            errors.push(format!("missing table file {} for {}", path.display(), table.table));
            continue;
        }

        let actual_sha = match sha256_file(&path) {
            Ok(x) => x,
            Err(e) => {
                errors.push(e);
                continue;
            }
        };
        let actual_rows = match count_gzip_jsonl_rows(&path) {
            Ok(x) => x,
            Err(e) => {
                errors.push(e);
                continue;
            }
        };
        let compressed_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);

        let rows_ok = actual_rows == table.rows;
        let sha_ok = actual_sha == table.sha256;
        if !rows_ok {
            errors.push(format!(
                "row mismatch for {}: expected {}, got {}",
                table.table, table.rows, actual_rows
            ));
        }
        if !sha_ok {
            errors.push(format!("sha mismatch for {}", table.table));
        }

        total_rows += actual_rows;
        total_compressed_bytes += compressed_bytes;

        results.push(TableVerifyResult {
            table: table.table.clone(),
            file_path: path.display().to_string(),
            expected_rows: table.rows,
            actual_rows,
            expected_sha256: table.sha256.clone(),
            actual_sha256: actual_sha,
            rows_ok,
            sha_ok,
            compressed_bytes,
        });
    }

    Ok(PackVerifyResult {
        ok: errors.is_empty(),
        pack_name: manifest.pack_name,
        sport: manifest.sport,
        tables_checked: results.len(),
        total_rows,
        total_compressed_bytes,
        results,
        errors,
    })
}

pub fn table_rows_as_json(pack_dir: &Path, table_name: &str, limit: usize) -> Result<Vec<Value>, String> {
    let manifest = load_manifest(pack_dir)?;
    let table = manifest
        .tables
        .iter()
        .find(|t| t.table == table_name)
        .ok_or_else(|| format!("table not found in manifest: {}", table_name))?;
    let path = resolve_table_path(pack_dir, table);
    if !path.exists() {
        return Err(format!("table file missing: {}", path.display()));
    }

    let file = File::open(&path).map_err(|e| format!("failed to open {}: {}", path.display(), e))?;
    let decoder = GzDecoder::new(file);
    let reader = BufReader::new(decoder);

    let mut rows = Vec::new();
    for line in reader.lines().take(limit) {
        let line = line.map_err(|e| format!("failed reading {}: {}", path.display(), e))?;
        let value: Value = serde_json::from_str(&line)
            .map_err(|e| format!("failed to parse JSONL row in {}: {}", path.display(), e))?;
        rows.push(value);
    }
    Ok(rows)
}
