use crate::{HistoricalSourceFileContract, HistoricalSourceFileEntry};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalSourceVerificationReport {
    pub schema: String,
    pub manifest_id: String,
    pub ok: bool,
    pub files_checked: usize,
    pub files_verified: usize,
    pub total_declared_rows: u64,
    pub total_observed_rows: u64,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalSourceVerificationRow {
    pub task_id: String,
    pub relative_path: String,
    pub exists: bool,
    pub sha256_ok: bool,
    pub row_count_ok: bool,
    pub observed_rows: u64,
}

pub fn verify_historical_source_files(
    manifest: &HistoricalSourceFileContract,
    root_dir: &Path,
) -> HistoricalSourceVerificationReport {
    let mut errors = Vec::new();
    let mut files_verified = 0usize;
    let mut total_declared_rows = 0u64;
    let mut total_observed_rows = 0u64;

    if !manifest.offline_only || manifest.network_calls_allowed || !manifest.paper_only {
        errors.push("verification requires offline-only, no-network, paper-only manifest".to_string());
    }
    if manifest.files.is_empty() {
        errors.push("verification requires at least one source file".to_string());
    }

    for file in &manifest.files {
        total_declared_rows += file.row_count;
        match verify_one_source_file(file, root_dir) {
            Ok(row) => {
                total_observed_rows += row.observed_rows;
                if row.exists && row.sha256_ok && row.row_count_ok {
                    files_verified += 1;
                } else {
                    if !row.exists {
                        errors.push(format!("source file missing: {}", file.task_id));
                    }
                    if !row.sha256_ok {
                        errors.push(format!("source file sha256 mismatch: {}", file.task_id));
                    }
                    if !row.row_count_ok {
                        errors.push(format!("source file row count mismatch: {}", file.task_id));
                    }
                }
            }
            Err(err) => errors.push(format!("{}: {}", file.task_id, err)),
        }
    }

    HistoricalSourceVerificationReport {
        schema: "omnibet.historical_source_verification_report.v248".to_string(),
        manifest_id: manifest.manifest_id.clone(),
        ok: errors.is_empty(),
        files_checked: manifest.files.len(),
        files_verified,
        total_declared_rows,
        total_observed_rows,
        import_allowed_now: false,
        promotion_allowed: false,
        errors,
    }
}

pub fn verify_one_source_file(
    file: &HistoricalSourceFileEntry,
    root_dir: &Path,
) -> Result<HistoricalSourceVerificationRow, String> {
    validate_relative_path(&file.relative_path)?;
    if file.import_allowed_now || file.credentials_stored || file.network_calls_performed {
        return Err("unsafe source file flags are set".to_string());
    }
    let path = root_dir.join(&file.relative_path);
    if !path.exists() {
        return Ok(HistoricalSourceVerificationRow {
            task_id: file.task_id.clone(),
            relative_path: file.relative_path.clone(),
            exists: false,
            sha256_ok: false,
            row_count_ok: false,
            observed_rows: 0,
        });
    }
    if !path.is_file() {
        return Err("source path is not a file".to_string());
    }
    let observed_sha = sha256_path(&path).map_err(|e| format!("sha256 read failed: {}", e))?;
    let observed_rows = count_rows_for_codec(&path, &file.codec)?;
    Ok(HistoricalSourceVerificationRow {
        task_id: file.task_id.clone(),
        relative_path: file.relative_path.clone(),
        exists: true,
        sha256_ok: observed_sha == file.sha256.to_ascii_lowercase(),
        row_count_ok: observed_rows == file.row_count,
        observed_rows,
    })
}

pub fn sha256_path(path: &Path) -> std::io::Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 16 * 1024];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

pub fn count_rows_for_codec(path: &Path, codec: &str) -> Result<u64, String> {
    match codec {
        "json" => Ok(1),
        "csv" | "jsonl.gzip" => count_text_lines(path),
        other => Err(format!("unsupported verification codec: {}", other)),
    }
}

fn count_text_lines(path: &Path) -> Result<u64, String> {
    let file = File::open(path).map_err(|e| format!("open file: {}", e))?;
    let reader = BufReader::new(file);
    let mut rows = 0u64;
    for line in reader.lines() {
        let line = line.map_err(|e| format!("read line: {}", e))?;
        if !line.trim().is_empty() {
            rows += 1;
        }
    }
    Ok(rows)
}

fn validate_relative_path(value: &str) -> Result<(), String> {
    if value.trim().is_empty() {
        return Err("relative path is empty".to_string());
    }
    let path = PathBuf::from(value);
    if path.is_absolute() {
        return Err("relative path must not be absolute".to_string());
    }
    for component in path.components() {
        if matches!(component, std::path::Component::ParentDir) {
            return Err("relative path must not contain parent traversal".to_string());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{HistoricalSourceFileAcceptance, HistoricalSourceFileEntry};
    use std::fs;

    fn test_root(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(name);
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create temp root");
        dir
    }

    fn base_manifest(root: &Path) -> HistoricalSourceFileContract {
        let rel = "data/test/fixture_rows.csv";
        let path = root.join(rel);
        fs::create_dir_all(path.parent().expect("parent")).expect("create parent");
        let mut out = File::create(&path).expect("create fixture file");
        writeln!(out, "fixture_id,home,away").expect("write header");
        writeln!(out, "1,A,B").expect("write row");
        let sha = sha256_path(&path).expect("hash fixture");
        HistoricalSourceFileContract {
            schema: "omnibet.historical_source_file_manifest.v247".to_string(),
            manifest_id: "v248_test_manifest".to_string(),
            created_at: "2026-06-21T00:00:00Z".to_string(),
            source_plan_id: "v247_test_plan".to_string(),
            offline_only: true,
            network_calls_allowed: false,
            paper_only: true,
            file_exists_check_required_for_real_import: true,
            files: vec![HistoricalSourceFileEntry {
                task_id: "window_a::fixture_results_source".to_string(),
                window_id: "window_a".to_string(),
                source_id: "fixture_results_source".to_string(),
                source_kind: "fixtures_results".to_string(),
                relative_path: rel.to_string(),
                codec: "csv".to_string(),
                row_count: 2,
                sha256: sha,
                snapshot_cutoff_utc: "2026-06-01T00:00:00Z".to_string(),
                point_in_time_timestamp_present: true,
                provider_identity_mapping_required: true,
                market_mapping_required: false,
                credentials_stored: false,
                network_calls_performed: false,
                import_allowed_now: false,
            }],
            acceptance: HistoricalSourceFileAcceptance {
                rust_source_file_types_added: true,
                task_alignment_validation_added: true,
                sha256_validation_added: true,
                row_count_validation_added: true,
                source_safety_validation_added: true,
                python_smoke_added: true,
                ci_workflow_added: true,
            },
        }
    }

    #[test]
    fn verifies_existing_file_hash_and_rows() {
        let root = test_root("omnibet_v248_verify_ok");
        let manifest = base_manifest(&root);
        let report = verify_historical_source_files(&manifest, &root);
        assert!(report.ok, "{:?}", report.errors);
        assert_eq!(report.files_checked, 1);
        assert_eq!(report.files_verified, 1);
        assert_eq!(report.total_declared_rows, 2);
        assert_eq!(report.total_observed_rows, 2);
        assert!(!report.import_allowed_now);
        assert!(!report.promotion_allowed);
    }

    #[test]
    fn rejects_missing_file_and_bad_hash() {
        let root = test_root("omnibet_v248_verify_bad");
        let mut manifest = base_manifest(&root);
        manifest.files[0].sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".to_string();
        let report = verify_historical_source_files(&manifest, &root);
        assert!(!report.ok);
        assert!(report.errors.iter().any(|err| err.contains("sha256")));
        manifest.files[0].relative_path = "missing/file.csv".to_string();
        let report = verify_historical_source_files(&manifest, &root);
        assert!(!report.ok);
        assert!(report.errors.iter().any(|err| err.contains("missing")));
    }

    #[test]
    fn rejects_path_traversal() {
        let root = test_root("omnibet_v248_verify_path");
        let mut manifest = base_manifest(&root);
        manifest.files[0].relative_path = "../secret.csv".to_string();
        let report = verify_historical_source_files(&manifest, &root);
        assert!(!report.ok);
        assert!(report.errors.iter().any(|err| err.contains("parent traversal")));
    }
}
