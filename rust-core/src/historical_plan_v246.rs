use crate::{parse_historical_import_contract, validate_historical_import_contract, HistoricalImportContract};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportPlanPreview {
    pub schema: String,
    pub plan_id: String,
    pub created_at: String,
    pub source_contract_id: String,
    pub offline_only: bool,
    pub network_calls_allowed: bool,
    pub paper_only: bool,
    pub target_layer: String,
    pub window_count: usize,
    pub required_source_count: usize,
    pub tasks: Vec<HistoricalImportPlanTask>,
    pub total_tasks: usize,
    pub blocked: bool,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HistoricalImportPlanTask {
    pub task_id: String,
    pub window_id: String,
    pub source_id: String,
    pub source_kind: String,
    pub competition_id: String,
    pub season: String,
    pub start_date: String,
    pub end_date: String,
    pub snapshot_cutoff_utc: String,
    pub point_in_time_timestamp_required: bool,
    pub provider_identity_mapping_required: bool,
    pub market_mapping_required: bool,
    pub credentials_must_not_be_persisted: bool,
    pub import_allowed_now: bool,
    pub required_next_artifact: String,
}

pub fn build_historical_import_plan_preview(
    contract: &HistoricalImportContract,
    plan_id: &str,
    created_at: &str,
) -> HistoricalImportPlanPreview {
    let validation = validate_historical_import_contract(contract);
    let mut tasks = Vec::new();
    if validation.ok {
        for window in &contract.import_windows {
            for source in contract.source_requirements.iter().filter(|src| src.required) {
                tasks.push(HistoricalImportPlanTask {
                    task_id: format!("{}::{}", window.window_id, source.source_id),
                    window_id: window.window_id.clone(),
                    source_id: source.source_id.clone(),
                    source_kind: source.source_kind.clone(),
                    competition_id: window.competition_id.clone(),
                    season: window.season.clone(),
                    start_date: window.start_date.clone(),
                    end_date: window.end_date.clone(),
                    snapshot_cutoff_utc: window.snapshot_cutoff_utc.clone(),
                    point_in_time_timestamp_required: source.point_in_time_timestamp_required,
                    provider_identity_mapping_required: source.provider_identity_mapping_required,
                    market_mapping_required: source.market_mapping_required,
                    credentials_must_not_be_persisted: source.credentials_must_not_be_persisted,
                    import_allowed_now: false,
                    required_next_artifact: "offline_file_manifest_with_sha256_and_row_count".to_string(),
                });
            }
        }
    }
    let total_tasks = tasks.len();
    HistoricalImportPlanPreview {
        schema: "omnibet.historical_import_plan_preview.v246".to_string(),
        plan_id: plan_id.to_string(),
        created_at: created_at.to_string(),
        source_contract_id: contract.import_id.clone(),
        offline_only: true,
        network_calls_allowed: false,
        paper_only: true,
        target_layer: contract.target_layer.clone(),
        window_count: contract.import_windows.len(),
        required_source_count: contract.source_requirements.iter().filter(|src| src.required).count(),
        tasks,
        total_tasks,
        blocked: !validation.ok,
        errors: validation.errors,
    }
}

pub fn build_historical_import_plan_preview_from_contract_text(
    contract_text: &str,
    plan_id: &str,
    created_at: &str,
) -> Result<HistoricalImportPlanPreview, String> {
    let contract = parse_historical_import_contract(contract_text)
        .map_err(|e| format!("parse historical import contract: {}", e))?;
    Ok(build_historical_import_plan_preview(&contract, plan_id, created_at))
}

pub fn build_default_historical_import_plan_preview(created_at: &str) -> Result<HistoricalImportPlanPreview, String> {
    build_historical_import_plan_preview_from_contract_text(
        include_str!("../../configs/historical_import_contract.v245.json"),
        "v246_offline_historical_import_plan_preview",
        created_at,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_plan_tasks_from_valid_contract() {
        let plan = build_default_historical_import_plan_preview("2026-06-21T00:00:00Z")
            .expect("build historical import plan preview");
        assert_eq!(plan.schema, "omnibet.historical_import_plan_preview.v246");
        assert!(!plan.blocked, "{:?}", plan.errors);
        assert!(plan.offline_only);
        assert!(!plan.network_calls_allowed);
        assert!(plan.paper_only);
        assert_eq!(plan.window_count, 2);
        assert_eq!(plan.required_source_count, 3);
        assert_eq!(plan.total_tasks, 6);
        assert!(plan.tasks.iter().any(|task| {
            task.window_id == "sample_world_cup_2026_matchday_window"
                && task.source_id == "odds_snapshot_source"
                && task.market_mapping_required
                && !task.import_allowed_now
        }));
    }

    #[test]
    fn blocked_contract_yields_no_tasks() {
        let mut contract = parse_historical_import_contract(
            include_str!("../../configs/historical_import_contract.v245.json"),
        )
        .expect("parse contract");
        contract.network_calls_allowed_in_ci = true;
        let plan = build_historical_import_plan_preview(
            &contract,
            "blocked_plan",
            "2026-06-21T00:00:00Z",
        );
        assert!(plan.blocked);
        assert_eq!(plan.total_tasks, 0);
        assert!(plan.errors.iter().any(|err| err.contains("network calls")));
    }
}
