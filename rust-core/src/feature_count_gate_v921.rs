use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FeatureCountGateConfigV921 {
    pub min_required_rows: usize,
    pub source_label: String,
}

impl Default for FeatureCountGateConfigV921 {
    fn default() -> Self {
        Self {
            min_required_rows: 200,
            source_label: "canonical_matches".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FeatureCountSkippedRowV921 {
    pub row_number: usize,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FeatureCountGateReportV921 {
    pub schema: String,
    pub generated_by: String,
    pub source_label: String,
    pub min_required_rows: usize,
    pub input_rows: usize,
    pub parsed_rows: usize,
    pub completed_match_rows: usize,
    pub eligible_feature_rows: usize,
    pub duplicate_match_rows: usize,
    pub skipped_rows: Vec<FeatureCountSkippedRowV921>,
    pub ready: bool,
    pub status: String,
    pub baseline_training_allowed: bool,
    pub real_model_ready: bool,
    pub model_status: String,
    pub notes: Vec<String>,
}

pub fn build_feature_count_gate_report_v921(
    matches_jsonl: &str,
    config: &FeatureCountGateConfigV921,
) -> Result<FeatureCountGateReportV921, String> {
    let mut input_rows = 0;
    let mut parsed_rows = 0;
    let mut completed_match_rows = 0;
    let mut eligible_feature_rows = 0;
    let mut duplicate_match_rows = 0;
    let mut skipped_rows = Vec::new();
    let mut seen_match_ids = BTreeSet::new();

    for (idx, line) in matches_jsonl.lines().enumerate() {
        let row_number = idx + 1;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        input_rows += 1;
        let value: Value = match serde_json::from_str(line) {
            Ok(value) => value,
            Err(err) => {
                skipped_rows.push(FeatureCountSkippedRowV921 {
                    row_number,
                    reason: format!("invalid_json:{err}"),
                });
                continue;
            }
        };
        parsed_rows += 1;
        let source_match_id = first_string_v921(&value, &["source_match_id", "match_id", "fixture_id"]);
        let Some(match_id) = source_match_id else {
            skipped_rows.push(FeatureCountSkippedRowV921 {
                row_number,
                reason: "missing_match_id".to_string(),
            });
            continue;
        };
        if !seen_match_ids.insert(match_id.clone()) {
            duplicate_match_rows += 1;
            skipped_rows.push(FeatureCountSkippedRowV921 {
                row_number,
                reason: format!("duplicate_match_id:{match_id}"),
            });
            continue;
        }

        if !is_completed_match_v921(&value) {
            skipped_rows.push(FeatureCountSkippedRowV921 {
                row_number,
                reason: "not_completed_final_match".to_string(),
            });
            continue;
        }
        completed_match_rows += 1;

        match eligibility_reason_v921(&value) {
            None => eligible_feature_rows += 1,
            Some(reason) => skipped_rows.push(FeatureCountSkippedRowV921 { row_number, reason }),
        }
    }

    let ready = eligible_feature_rows >= config.min_required_rows;
    let status = if ready {
        "ready_for_baseline_count_gate"
    } else {
        "needs_more_rows"
    };
    let mut notes = vec![
        "Counts only training-eligible completed match feature rows, not generic sample/event rows.".to_string(),
        "This is a count gate only; model quality still requires walk-forward evaluation and calibration.".to_string(),
        "real_model_ready remains false until a later evaluation gate passes.".to_string(),
    ];
    if !ready {
        notes.push(format!(
            "Need {} more eligible rows to reach the minimum {} row baseline gate.",
            config.min_required_rows.saturating_sub(eligible_feature_rows),
            config.min_required_rows
        ));
    }

    Ok(FeatureCountGateReportV921 {
        schema: "omnibet.feature_count_gate.v921".to_string(),
        generated_by: "omnibet-feature-count-gate".to_string(),
        source_label: config.source_label.clone(),
        min_required_rows: config.min_required_rows,
        input_rows,
        parsed_rows,
        completed_match_rows,
        eligible_feature_rows,
        duplicate_match_rows,
        skipped_rows,
        ready,
        status: status.to_string(),
        baseline_training_allowed: ready,
        real_model_ready: false,
        model_status: if ready {
            "count_gate_passed_eval_required".to_string()
        } else {
            "locked_needs_more_rows".to_string()
        },
        notes,
    })
}

pub fn write_feature_count_gate_report_v921(report: &FeatureCountGateReportV921, out_path: &Path) -> Result<(), String> {
    if let Some(parent) = out_path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
        }
    }
    let text = serde_json::to_string_pretty(report).map_err(|e| format!("serialize feature count report: {e}"))?;
    fs::write(out_path, format!("{text}\n")).map_err(|e| format!("write {}: {e}", out_path.display()))
}

fn is_completed_match_v921(value: &Value) -> bool {
    let status = first_string_v921(value, &["status", "match_status"])
        .unwrap_or_else(|| "final".to_string())
        .to_ascii_lowercase();
    matches!(status.as_str(), "final" | "finished" | "complete" | "completed" | "ft")
}

fn eligibility_reason_v921(value: &Value) -> Option<String> {
    if first_string_v921(value, &["match_date", "date", "kickoff_date"]).is_none() {
        return Some("missing_match_date".to_string());
    }
    if first_string_v921(value, &["home_team_raw", "home_team", "home_name"]).is_none() {
        return Some("missing_home_team".to_string());
    }
    if first_string_v921(value, &["away_team_raw", "away_team", "away_name"]).is_none() {
        return Some("missing_away_team".to_string());
    }
    if first_i64_v921(value, &["final_home_goals", "home_goals", "fthg"]).is_none() {
        return Some("missing_final_home_goals".to_string());
    }
    if first_i64_v921(value, &["final_away_goals", "away_goals", "ftag"]).is_none() {
        return Some("missing_final_away_goals".to_string());
    }
    None
}

fn first_string_v921(value: &Value, keys: &[&str]) -> Option<String> {
    for key in keys {
        let Some(raw) = value.get(*key) else { continue; };
        if let Some(text) = raw.as_str() {
            let text = text.trim();
            if !text.is_empty() {
                return Some(text.to_string());
            }
        }
    }
    None
}

fn first_i64_v921(value: &Value, keys: &[&str]) -> Option<i64> {
    for key in keys {
        let Some(raw) = value.get(*key) else { continue; };
        if let Some(number) = raw.as_i64() {
            return Some(number);
        }
        if let Some(text) = raw.as_str() {
            if let Ok(number) = text.trim().parse::<i64>() {
                return Some(number);
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reports_needs_more_rows_for_tiny_batch() {
        let jsonl = r#"{"source_match_id":"m1","match_date":"2024-08-16","home_team_raw":"A","away_team_raw":"B","final_home_goals":1,"final_away_goals":0,"status":"final"}
{"source_match_id":"m2","match_date":"2024-08-17","home_team_raw":"C","away_team_raw":"D","final_home_goals":0,"final_away_goals":0,"status":"final"}
{"source_match_id":"m3","match_date":"2024-08-18","home_team_raw":"E","away_team_raw":"F","final_home_goals":2,"final_away_goals":3,"status":"final"}
"#;
        let report = build_feature_count_gate_report_v921(jsonl, &FeatureCountGateConfigV921::default()).expect("count report");
        assert_eq!(report.input_rows, 3);
        assert_eq!(report.completed_match_rows, 3);
        assert_eq!(report.eligible_feature_rows, 3);
        assert!(!report.ready);
        assert!(!report.baseline_training_allowed);
        assert!(!report.real_model_ready);
        assert_eq!(report.status, "needs_more_rows");
    }

    #[test]
    fn passes_count_gate_when_minimum_is_met() {
        let mut jsonl = String::new();
        for idx in 0..5 {
            jsonl.push_str(&format!(
                "{{\"source_match_id\":\"m{idx}\",\"match_date\":\"2024-08-{day:02}\",\"home_team_raw\":\"A{idx}\",\"away_team_raw\":\"B{idx}\",\"final_home_goals\":1,\"final_away_goals\":0,\"status\":\"final\"}}\n",
                day = idx + 1
            ));
        }
        let config = FeatureCountGateConfigV921 {
            min_required_rows: 5,
            source_label: "test".to_string(),
        };
        let report = build_feature_count_gate_report_v921(&jsonl, &config).expect("count report");
        assert_eq!(report.eligible_feature_rows, 5);
        assert!(report.ready);
        assert!(report.baseline_training_allowed);
        assert!(!report.real_model_ready);
        assert_eq!(report.status, "ready_for_baseline_count_gate");
        assert_eq!(report.model_status, "count_gate_passed_eval_required");
    }

    #[test]
    fn skips_duplicates_incomplete_and_non_final_rows() {
        let jsonl = r#"{"source_match_id":"m1","match_date":"2024-08-16","home_team_raw":"A","away_team_raw":"B","final_home_goals":1,"final_away_goals":0,"status":"final"}
{"source_match_id":"m1","match_date":"2024-08-16","home_team_raw":"A","away_team_raw":"B","final_home_goals":1,"final_away_goals":0,"status":"final"}
{"source_match_id":"m2","match_date":"2024-08-17","home_team_raw":"C","away_team_raw":"D","final_home_goals":0,"status":"final"}
{"source_match_id":"m3","match_date":"2024-08-18","home_team_raw":"E","away_team_raw":"F","status":"scheduled"}
not-json
"#;
        let config = FeatureCountGateConfigV921 {
            min_required_rows: 1,
            source_label: "test".to_string(),
        };
        let report = build_feature_count_gate_report_v921(jsonl, &config).expect("count report");
        assert_eq!(report.input_rows, 5);
        assert_eq!(report.parsed_rows, 4);
        assert_eq!(report.completed_match_rows, 2);
        assert_eq!(report.eligible_feature_rows, 1);
        assert_eq!(report.duplicate_match_rows, 1);
        assert_eq!(report.skipped_rows.len(), 4);
        assert!(report.ready);
    }
}
