use crate::{
    build_provider_normalization_preview_v255, validate_provider_adapter_contracts_v254_text,
    ProviderAdapterValidationReportV254, ProviderNormalizationPreviewBundleV255,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SourceTerminalReportV256 {
    pub schema: String,
    pub report_id: String,
    pub created_at: String,
    pub paper_only: bool,
    pub quarantine_only: bool,
    pub source_terminal_visible: bool,
    pub adapter_count: usize,
    pub adapter_ok_count: usize,
    pub normalized_total_rows: usize,
    pub normalized_row_counts: BTreeMap<String, usize>,
    pub readiness: SourceTerminalReadinessV256,
    pub desktop_actions: SourceTerminalDesktopActionsV256,
    pub blocker_summary: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SourceTerminalReadinessV256 {
    pub adapter_health_ok: bool,
    pub normalization_preview_ok: bool,
    pub ready_for_source_panel: bool,
    pub ready_for_bronze_write: bool,
    pub ready_for_evaluation: bool,
    pub ready_for_training: bool,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SourceTerminalDesktopActionsV256 {
    pub inspect_adapters: bool,
    pub inspect_rows: bool,
    pub export_report: bool,
    pub live_fetch: bool,
    pub promote_to_bronze: bool,
    pub run_evaluation: bool,
    pub train_model: bool,
    pub place_bets: bool,
}

pub fn build_source_terminal_report_v256(
    adapter_report: &ProviderAdapterValidationReportV254,
    normalization: &ProviderNormalizationPreviewBundleV255,
    report_id: &str,
    created_at: &str,
) -> SourceTerminalReportV256 {
    let adapter_ok_count = adapter_report
        .health_rows
        .iter()
        .filter(|row| row.contract_ok && row.fixture_loaded)
        .count();
    let mut blocker_summary = Vec::new();
    blocker_summary.extend(adapter_report.blockers.iter().map(|item| format!("adapter:{}", item)));
    blocker_summary.extend(normalization.blockers.iter().map(|item| format!("normalization:{}", item)));

    let adapter_health_ok = adapter_report.ok && adapter_ok_count == adapter_report.adapter_count;
    let normalization_preview_ok = normalization.blockers.is_empty() && normalization.total_rows > 0;
    let ready_for_source_panel = adapter_health_ok && normalization_preview_ok;
    let readiness = SourceTerminalReadinessV256 {
        adapter_health_ok,
        normalization_preview_ok,
        ready_for_source_panel,
        ready_for_bronze_write: false,
        ready_for_evaluation: false,
        ready_for_training: false,
        reason: if ready_for_source_panel {
            "offline_source_terminal_preview_ready_but_quarantined".to_string()
        } else {
            "source_terminal_has_blockers".to_string()
        },
    };

    SourceTerminalReportV256 {
        schema: "omnibet.source_terminal_report.v256".to_string(),
        report_id: report_id.to_string(),
        created_at: created_at.to_string(),
        paper_only: true,
        quarantine_only: true,
        source_terminal_visible: ready_for_source_panel,
        adapter_count: adapter_report.adapter_count,
        adapter_ok_count,
        normalized_total_rows: normalization.total_rows,
        normalized_row_counts: normalization.row_counts.clone(),
        readiness,
        desktop_actions: locked_desktop_actions_v256(),
        blocker_summary,
    }
}

pub fn build_default_source_terminal_report_v256(
    report_id: &str,
    created_at: &str,
) -> Result<SourceTerminalReportV256, String> {
    let adapter_report = validate_provider_adapter_contracts_v254_text(
        include_str!("../../configs/provider_adapter_contracts.v254.json"),
        include_str!("../../data/provider_fixtures/v254/odds_provider_snapshot.sample.json"),
        include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
    )?;
    let normalization = build_provider_normalization_preview_v255(
        include_str!("../../data/provider_fixtures/v254/odds_provider_snapshot.sample.json"),
        include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
        "v255_default_source_terminal_input",
        created_at,
    )?;
    Ok(build_source_terminal_report_v256(
        &adapter_report,
        &normalization,
        report_id,
        created_at,
    ))
}

fn locked_desktop_actions_v256() -> SourceTerminalDesktopActionsV256 {
    SourceTerminalDesktopActionsV256 {
        inspect_adapters: true,
        inspect_rows: true,
        export_report: true,
        live_fetch: false,
        promote_to_bronze: false,
        run_evaluation: false,
        train_model: false,
        place_bets: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_source_terminal_report_from_offline_fixtures() {
        let report = build_default_source_terminal_report_v256(
            "v256_test_report",
            "2026-06-21T00:00:00Z",
        )
        .expect("build report");
        assert_eq!(report.schema, "omnibet.source_terminal_report.v256");
        assert!(report.paper_only);
        assert!(report.quarantine_only);
        assert!(report.source_terminal_visible);
        assert_eq!(report.adapter_count, 2);
        assert_eq!(report.adapter_ok_count, 2);
        assert_eq!(report.normalized_total_rows, 5);
        assert_eq!(report.normalized_row_counts["odds_snapshot_candidate"], 3);
        assert_eq!(report.normalized_row_counts["fixture_result_candidate"], 1);
        assert_eq!(report.normalized_row_counts["event_context_candidate"], 1);
        assert!(report.readiness.ready_for_source_panel);
        assert!(!report.readiness.ready_for_bronze_write);
        assert!(!report.readiness.ready_for_evaluation);
        assert!(!report.readiness.ready_for_training);
        assert!(report.desktop_actions.inspect_rows);
        assert!(report.desktop_actions.export_report);
        assert!(!report.desktop_actions.live_fetch);
        assert!(!report.desktop_actions.promote_to_bronze);
        assert!(!report.desktop_actions.run_evaluation);
        assert!(!report.desktop_actions.train_model);
        assert!(!report.desktop_actions.place_bets);
        assert!(report.blocker_summary.is_empty());
    }

    #[test]
    fn source_terminal_remains_visible_blocked_when_normalization_has_blockers() {
        let adapter_report = validate_provider_adapter_contracts_v254_text(
            include_str!("../../configs/provider_adapter_contracts.v254.json"),
            include_str!("../../data/provider_fixtures/v254/odds_provider_snapshot.sample.json"),
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
        )
        .expect("adapter report");
        let mut normalization = build_provider_normalization_preview_v255(
            "{}",
            include_str!("../../data/provider_fixtures/v254/football_fixture_event.sample.json"),
            "v255_bad_input",
            "2026-06-21T00:00:00Z",
        )
        .expect("normalization with blocker");
        normalization.blockers.push("manual_blocker".to_string());
        let report = build_source_terminal_report_v256(
            &adapter_report,
            &normalization,
            "v256_bad_report",
            "2026-06-21T00:00:00Z",
        );
        assert!(!report.source_terminal_visible);
        assert!(!report.readiness.normalization_preview_ok);
        assert!(!report.readiness.ready_for_bronze_write);
        assert!(report.blocker_summary.iter().any(|item| item.contains("normalization")));
        assert!(!report.desktop_actions.live_fetch);
        assert!(!report.desktop_actions.train_model);
    }
}
