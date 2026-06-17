use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CompetitionRowCounts {
    pub competitions: usize,
    pub history: usize,
    pub training: usize,
    pub eval_predictions: usize,
    pub source_coverage_rows: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CompetitionReportManifest {
    pub ok: bool,
    pub schema: String,
    pub row_counts: CompetitionRowCounts,
    pub best_model: String,
}

pub fn parse_competition_report(text: &str) -> Result<CompetitionReportManifest, serde_json::Error> {
    serde_json::from_str::<CompetitionReportManifest>(text)
}

pub fn validate_competition_report(m: &CompetitionReportManifest) -> Result<(), String> {
    if !m.ok {
        return Err("report not ok".to_string());
    }
    if m.row_counts.competitions == 0 {
        return Err("no competition rows".to_string());
    }
    if m.row_counts.history != m.row_counts.training {
        return Err("row count mismatch".to_string());
    }
    if m.best_model.trim().is_empty() {
        return Err("missing model id".to_string());
    }
    Ok(())
}
