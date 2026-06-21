use crate::{build_default_historical_import_plan_preview, HistoricalImportPlanPreview};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalFileManifestContract {
    pub schema: String,
    pub manifest_id: String,
    pub created_at: String,
    pub source_plan_id: String,
    pub offline_only: bool,
    pub network_calls_allowed: bool,
    pub paper_only: bool,
    pub file_exists_check_required_for_real_import: bool,
    pub files: Vec<HistoricalFileManifestEntry>,
    pub acceptance: HistoricalFileManifestAcceptance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalFileManifestEntry {
    pub task_id: String,
    pub window_id: String,
    pub source_id: String,
    pub source_kind: String,
    pub relative_path: String,
    pub codec: String,
    pub row_count: u64,
    pub sha256: String,
    pub snapshot_cutoff_utc: String,
    pub point_in_time_timestamp_present: bool,
    pub provider_identity_mapping_required: bool,
    pub market_mapping_required: bool,
    pub credentials_stored: bool,
    pub network_calls_performed: bool,
    pub import_allowed_now: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalFileManifestAcceptance {
    pub rust_manifest_types_added: bool,
    pub task_alignment_validation_added: bool,
    pub sha256_validation_added: bool,
    pub row_count_validation_added: bool,
    pub source_safety_validation_added: bool,
    pub python_smoke_added: bool,
    pub ci_workflow_added: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalFileManifestValidationReport {
    pub schema: String,
    pub manifest_id: String,
    pub ok: bool,
    pub expected_task_count: usize,
    pub file_count: usize,
    pub total_rows: u64,
    pub errors: Vec<String>,
}

pub fn parse_historical_file_manifest(text: &str) -> Result<HistoricalFileManifestContract, serde_json::Error> {
    serde_json::from_str(text)
}

pub fn validate_historical_file_manifest_against_plan(
    manifest: &HistoricalFileManifestContract,
    plan: &HistoricalImportPlanPreview,
) -> HistoricalFileManifestValidationReport {
    let mut errors = Vec::new();
    if manifest.schema != "omnibet.historical_file_manifest.v247" {
        errors.push(format!("unexpected historical file manifest schema: {}", manifest.schema));
    }
    if !manifest.offline_only || manifest.network_calls_allowed || !manifest.paper_only {
        errors.push("manifest must be offline-only, no-network, and paper-only".to_string());
    }
    if !manifest.file_exists_check_required_for_real_import {
        errors.push("real import must require file existence checks".to_string());
    }
    if manifest.source_plan_id != plan.plan_id {
        errors.push(format!("manifest source plan mismatch: {}", manifest.source_plan_id));
    }
    if plan.blocked {
        errors.push("source plan is blocked".to_string());
    }

    let mut expected_tasks = BTreeMap::new();
    for task in &plan.tasks {
        expected_tasks.insert(task.task_id.clone(), task);
    }
    let mut seen_tasks = BTreeSet::new();
    let mut total_rows = 0u64;
    for file in &manifest.files {
        if !seen_tasks.insert(file.task_id.clone()) {
            errors.push(format!("duplicate file task id: {}", file.task_id));
        }
        let Some(task) = expected_tasks.get(&file.task_id) else {
            errors.push(format!("file task not present in plan: {}", file.task_id));
            continue;
        };
        if file.window_id != task.window_id || file.source_id != task.source_id || file.source_kind != task.source_kind {
            errors.push(format!("file task metadata mismatch: {}", file.task_id));
        }
        if file.snapshot_cutoff_utc != task.snapshot_cutoff_utc {
            errors.push(format!("snapshot cutoff mismatch: {}", file.task_id));
        }
        if !file.point_in_time_timestamp_present {
            errors.push(format!("missing point-in-time timestamp marker: {}", file.task_id));
        }
        if !file.provider_identity_mapping_required || file.market_mapping_required != task.market_mapping_required {
            errors.push(format!("mapping requirement mismatch: {}", file.task_id));
        }
        if file.credentials_stored || file.network_calls_performed || file.import_allowed_now {
            errors.push(format!("unsafe file flags: {}", file.task_id));
        }
        if file.relative_path.trim().is_empty() || file.relative_path.starts_with('/') || file.relative_path.contains("..") {
            errors.push(format!("unsafe relative path: {}", file.task_id));
        }
        if file.codec != "jsonl.gzip" && file.codec != "csv" && file.codec != "json" {
            errors.push(format!("unsupported candidate file codec: {}", file.codec));
        }
        if file.row_count == 0 {
            errors.push(format!("candidate file row count must be non-zero: {}", file.task_id));
        }
        if !is_hex_sha256(&file.sha256) {
            errors.push(format!("invalid sha256: {}", file.task_id));
        }
        total_rows += file.row_count;
    }

    if manifest.files.len() != expected_tasks.len() {
        errors.push(format!("file count mismatch: expected {} got {}", expected_tasks.len(), manifest.files.len()));
    }
    for task_id in expected_tasks.keys() {
        if !seen_tasks.contains(task_id) {
            errors.push(format!("missing file for task: {}", task_id));
        }
    }

    HistoricalFileManifestValidationReport {
        schema: "omnibet.historical_file_manifest_validation_report.v247".to_string(),
        manifest_id: manifest.manifest_id.clone(),
        ok: errors.is_empty(),
        expected_task_count: expected_tasks.len(),
        file_count: manifest.files.len(),
        total_rows,
        errors,
    }
}

pub fn validate_historical_file_manifest_text(
    manifest_text: &str,
    created_at: &str,
) -> Result<HistoricalFileManifestValidationReport, String> {
    let manifest = parse_historical_file_manifest(manifest_text)
        .map_err(|e| format!("parse historical file manifest: {}", e))?;
    let plan = build_default_historical_import_plan_preview(created_at)?;
    Ok(validate_historical_file_manifest_against_plan(&manifest, &plan))
}

fn is_hex_sha256(value: &str) -> bool {
    value.len() == 64 && value.chars().all(|ch| ch.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_file_manifest_against_plan() {
        let report = validate_historical_file_manifest_text(
            include_str!("../../configs/historical_file_manifest.v247.json"),
            "2026-06-21T00:00:00Z",
        )
        .expect("validate file manifest");
        assert!(report.ok, "{:?}", report.errors);
        assert_eq!(report.expected_task_count, 6);
        assert_eq!(report.file_count, 6);
        assert_eq!(report.total_rows, 600);
    }

    #[test]
    fn rejects_unknown_task_and_bad_hash() {
        let mut manifest = parse_historical_file_manifest(
            include_str!("../../configs/historical_file_manifest.v247.json"),
        )
        .expect("parse manifest");
        manifest.files[0].task_id = "unknown_task".to_string();
        manifest.files[0].sha256 = "bad".to_string();
        let plan = build_default_historical_import_plan_preview("2026-06-21T00:00:00Z")
            .expect("build plan");
        let report = validate_historical_file_manifest_against_plan(&manifest, &plan);
        assert!(!report.ok);
        assert!(report.errors.iter().any(|err| err.contains("not present in plan")));
        assert!(report.errors.iter().any(|err| err.contains("invalid sha256")));
    }
}
