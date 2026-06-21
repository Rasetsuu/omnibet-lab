use crate::{verify_historical_source_files, HistoricalSourceFileContract};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeCandidatePreviewBundle {
    pub schema: String,
    pub bundle_id: String,
    pub created_at: String,
    pub source_manifest_id: String,
    pub source_verification_schema: String,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
    pub files_read: usize,
    pub total_rows: u64,
    pub rows: Vec<BronzeCandidatePreviewRow>,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BronzeCandidatePreviewRow {
    pub row_id: String,
    pub task_id: String,
    pub source_id: String,
    pub source_kind: String,
    pub relative_path: String,
    pub row_number: u64,
    pub raw_line_sha256: String,
    pub quarantine_only: bool,
    pub import_allowed_now: bool,
    pub promotion_allowed: bool,
    pub evaluation_allowed: bool,
    pub training_dataset_promotion_allowed: bool,
}

pub fn build_bronze_candidate_preview_bundle(
    manifest: &HistoricalSourceFileContract,
    root_dir: &Path,
    bundle_id: &str,
    created_at: &str,
) -> BronzeCandidatePreviewBundle {
    let verification = verify_historical_source_files(manifest, root_dir);
    let mut rows = Vec::new();
    let mut errors = verification.errors.clone();
    let mut files_read = 0usize;

    if verification.ok {
        for source in &manifest.files {
            let path = root_dir.join(&source.relative_path);
            match read_preview_rows_for_source(source, &path) {
                Ok(mut source_rows) => {
                    files_read += 1;
                    rows.append(&mut source_rows);
                }
                Err(err) => errors.push(format!("{}: {}", source.task_id, err)),
            }
        }
    }

    BronzeCandidatePreviewBundle {
        schema: "omnibet.bronze_candidate_preview_bundle.v249".to_string(),
        bundle_id: bundle_id.to_string(),
        created_at: created_at.to_string(),
        source_manifest_id: manifest.manifest_id.clone(),
        source_verification_schema: verification.schema,
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
        files_read,
        total_rows: rows.len() as u64,
        rows,
        errors,
    }
}

fn read_preview_rows_for_source(
    source: &crate::HistoricalSourceFileEntry,
    path: &Path,
) -> Result<Vec<BronzeCandidatePreviewRow>, String> {
    match source.codec.as_str() {
        "csv" | "jsonl.gzip" => read_text_preview_rows(source, path),
        "json" => read_json_preview_row(source, path),
        other => Err(format!("unsupported preview codec: {}", other)),
    }
}

fn read_text_preview_rows(
    source: &crate::HistoricalSourceFileEntry,
    path: &Path,
) -> Result<Vec<BronzeCandidatePreviewRow>, String> {
    let file = File::open(path).map_err(|e| format!("open source file: {}", e))?;
    let reader = BufReader::new(file);
    let mut rows = Vec::new();
    for line in reader.lines() {
        let line = line.map_err(|e| format!("read source line: {}", e))?;
        if line.trim().is_empty() {
            continue;
        }
        let row_number = rows.len() as u64 + 1;
        rows.push(build_preview_row(source, row_number, &line));
    }
    Ok(rows)
}

fn read_json_preview_row(
    source: &crate::HistoricalSourceFileEntry,
    path: &Path,
) -> Result<Vec<BronzeCandidatePreviewRow>, String> {
    let body = std::fs::read_to_string(path).map_err(|e| format!("read json source file: {}", e))?;
    Ok(vec![build_preview_row(source, 1, &body)])
}

fn build_preview_row(
    source: &crate::HistoricalSourceFileEntry,
    row_number: u64,
    raw_line: &str,
) -> BronzeCandidatePreviewRow {
    let raw_line_sha256 = sha256_text(raw_line);
    BronzeCandidatePreviewRow {
        row_id: format!("{}::row_{}", source.task_id, row_number),
        task_id: source.task_id.clone(),
        source_id: source.source_id.clone(),
        source_kind: source.source_kind.clone(),
        relative_path: source.relative_path.clone(),
        row_number,
        raw_line_sha256,
        quarantine_only: true,
        import_allowed_now: false,
        promotion_allowed: false,
        evaluation_allowed: false,
        training_dataset_promotion_allowed: false,
    }
}

fn sha256_text(value: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value.as_bytes());
    format!("{:x}", hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{sha256_path, HistoricalSourceFileAcceptance, HistoricalSourceFileEntry};
    use std::fs;
    use std::io::Write;
    use std::path::PathBuf;

    fn test_root(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(name);
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create temp root");
        dir
    }

    fn test_manifest(root: &Path) -> HistoricalSourceFileContract {
        let rel = "data/test/odds.csv";
        let path = root.join(rel);
        fs::create_dir_all(path.parent().expect("parent")).expect("create parent");
        let mut out = File::create(&path).expect("create source");
        writeln!(out, "fixture_id,market,price").expect("write header");
        writeln!(out, "1,1x2_home,2.10").expect("write row");
        let sha = sha256_path(&path).expect("hash source");
        HistoricalSourceFileContract {
            schema: "omnibet.historical_source_file_manifest.v247".to_string(),
            manifest_id: "v249_test_manifest".to_string(),
            created_at: "2026-06-21T00:00:00Z".to_string(),
            source_plan_id: "v249_test_plan".to_string(),
            offline_only: true,
            network_calls_allowed: false,
            paper_only: true,
            file_exists_check_required_for_real_import: true,
            files: vec![HistoricalSourceFileEntry {
                task_id: "window_a::odds_snapshot_source".to_string(),
                window_id: "window_a".to_string(),
                source_id: "odds_snapshot_source".to_string(),
                source_kind: "odds".to_string(),
                relative_path: rel.to_string(),
                codec: "csv".to_string(),
                row_count: 2,
                sha256: sha,
                snapshot_cutoff_utc: "2026-06-01T00:00:00Z".to_string(),
                point_in_time_timestamp_present: true,
                provider_identity_mapping_required: true,
                market_mapping_required: true,
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
    fn builds_quarantined_preview_rows_from_verified_source() {
        let root = test_root("omnibet_v249_preview_ok");
        let manifest = test_manifest(&root);
        let bundle = build_bronze_candidate_preview_bundle(
            &manifest,
            &root,
            "v249_test_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert!(bundle.errors.is_empty(), "{:?}", bundle.errors);
        assert_eq!(bundle.schema, "omnibet.bronze_candidate_preview_bundle.v249");
        assert_eq!(bundle.files_read, 1);
        assert_eq!(bundle.total_rows, 2);
        assert!(bundle.quarantine_only);
        assert!(!bundle.import_allowed_now);
        assert!(!bundle.promotion_allowed);
        assert!(!bundle.evaluation_allowed);
        assert!(!bundle.training_dataset_promotion_allowed);
        assert!(bundle.rows.iter().all(|row| row.quarantine_only));
        assert!(bundle.rows.iter().all(|row| !row.training_dataset_promotion_allowed));
    }

    #[test]
    fn blocked_when_source_verification_fails() {
        let root = test_root("omnibet_v249_preview_bad");
        let mut manifest = test_manifest(&root);
        manifest.files[0].sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".to_string();
        let bundle = build_bronze_candidate_preview_bundle(
            &manifest,
            &root,
            "v249_bad_bundle",
            "2026-06-21T00:00:00Z",
        );
        assert!(!bundle.errors.is_empty());
        assert_eq!(bundle.files_read, 0);
        assert_eq!(bundle.total_rows, 0);
        assert!(bundle.rows.is_empty());
    }
}
