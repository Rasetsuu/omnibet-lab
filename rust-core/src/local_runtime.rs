use crate::local_data_core::{
    build_training_rows, calibration_bands, coverage_report, dedupe_rows, metric_report, metrics_by_competition,
    CoverageReport, IntegrityReport, LocalPredictionRow, LocalResultRow, LocalTrainingRow, MetricReport,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeFeatureRow {
    pub competition_id: String,
    pub season: i32,
    pub source_event_id: String,
    pub rating_diff: f64,
    pub form_diff: f64,
    pub rest_diff: f64,
    pub label_home_win: u8,
    pub feature_cutoff: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeEvalRow {
    pub competition_id: String,
    pub season: i32,
    pub source_event_id: String,
    pub probability: f64,
    pub label_home_win: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeReport {
    pub ok: bool,
    pub schema: String,
    pub input_rows: usize,
    pub deduped_rows: usize,
    pub training_rows: usize,
    pub feature_rows: usize,
    pub evaluation_rows: usize,
    pub integrity: IntegrityReport,
    pub coverage: CoverageReport,
    pub global_metrics: MetricReport,
    pub metrics_by_competition: BTreeMap<String, MetricReport>,
    pub calibration_band_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeBridgePayload {
    pub ok: bool,
    pub schema: String,
    pub report: RuntimeReport,
    pub readiness: BTreeMap<String, bool>,
}

pub fn parse_result_rows_from_jsonl(text: &str) -> Result<Vec<LocalResultRow>, serde_json::Error> {
    let mut rows = Vec::new();
    for line in text.lines().filter(|line| !line.trim().is_empty()) {
        rows.push(serde_json::from_str::<LocalResultRow>(line)?);
    }
    Ok(rows)
}

pub fn training_to_feature_rows(rows: &[LocalTrainingRow]) -> Vec<RuntimeFeatureRow> {
    rows.iter()
        .map(|row| RuntimeFeatureRow {
            competition_id: row.competition_id.clone(),
            season: row.season,
            source_event_id: row.source_event_id.clone(),
            rating_diff: row.rating_diff,
            form_diff: row.form_diff,
            rest_diff: row.rest_diff,
            label_home_win: row.label_home_win,
            feature_cutoff: "pre_event_only".to_string(),
        })
        .collect()
}

fn clamp_probability(p: f64) -> f64 {
    p.clamp(0.02, 0.98)
}

fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x.clamp(-20.0, 20.0)).exp())
}

pub fn walk_forward_predictions(rows: &[RuntimeFeatureRow], first_test_season: i32) -> Vec<RuntimeEvalRow> {
    let mut out = Vec::new();
    let max_season = rows.iter().map(|row| row.season).max().unwrap_or(first_test_season);
    for test_season in first_test_season..=max_season {
        let train: Vec<&RuntimeFeatureRow> = rows.iter().filter(|row| row.season < test_season).collect();
        let test: Vec<&RuntimeFeatureRow> = rows.iter().filter(|row| row.season == test_season).collect();
        if train.is_empty() || test.is_empty() {
            continue;
        }
        let global_base = train.iter().map(|row| row.label_home_win as f64).sum::<f64>() / train.len() as f64;
        for row in test {
            let comp_train: Vec<&&RuntimeFeatureRow> = train.iter().filter(|train_row| train_row.competition_id == row.competition_id).collect();
            let base = if comp_train.is_empty() {
                global_base
            } else {
                comp_train.iter().map(|train_row| train_row.label_home_win as f64).sum::<f64>() / comp_train.len() as f64
            };
            let base = clamp_probability(base);
            let z = (base / (1.0 - base)).ln() + 0.85 * row.rating_diff + 0.55 * row.form_diff + 0.18 * row.rest_diff;
            out.push(RuntimeEvalRow {
                competition_id: row.competition_id.clone(),
                season: row.season,
                source_event_id: row.source_event_id.clone(),
                probability: clamp_probability(sigmoid(z)),
                label_home_win: row.label_home_win,
            });
        }
    }
    out
}

pub fn runtime_eval_to_core(rows: &[RuntimeEvalRow]) -> Vec<LocalPredictionRow> {
    rows.iter()
        .map(|row| LocalPredictionRow {
            competition_id: row.competition_id.clone(),
            probability: row.probability,
            label_home_win: row.label_home_win,
        })
        .collect()
}

pub fn build_runtime_report(rows: &[LocalResultRow], first_test_season: i32) -> RuntimeReport {
    let (deduped, integrity) = dedupe_rows(rows);
    let training = build_training_rows(&deduped);
    let features = training_to_feature_rows(&training);
    let eval = walk_forward_predictions(&features, first_test_season);
    let core_eval = runtime_eval_to_core(&eval);
    let calibration = calibration_bands(&core_eval);
    RuntimeReport {
        ok: integrity.ok && !training.is_empty() && !eval.is_empty(),
        schema: "omnibet.local_runtime_report.v117_v124".to_string(),
        input_rows: rows.len(),
        deduped_rows: deduped.len(),
        training_rows: training.len(),
        feature_rows: features.len(),
        evaluation_rows: eval.len(),
        integrity,
        coverage: coverage_report(&training),
        global_metrics: metric_report(&core_eval),
        metrics_by_competition: metrics_by_competition(&core_eval),
        calibration_band_count: calibration.len(),
    }
}

pub fn build_runtime_bridge_payload(rows: &[LocalResultRow], first_test_season: i32) -> RuntimeBridgePayload {
    let report = build_runtime_report(rows, first_test_season);
    let mut readiness = BTreeMap::new();
    readiness.insert("v117_loader".to_string(), true);
    readiness.insert("v118_integrity".to_string(), true);
    readiness.insert("v119_training".to_string(), true);
    readiness.insert("v120_coverage".to_string(), true);
    readiness.insert("v121_features".to_string(), true);
    readiness.insert("v122_walk_forward".to_string(), true);
    readiness.insert("v123_calibration".to_string(), true);
    readiness.insert("v124_bridge_payload".to_string(), true);
    RuntimeBridgePayload {
        ok: report.ok,
        schema: "omnibet.local_runtime_bridge.v124".to_string(),
        report,
        readiness,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_rows() -> Vec<LocalResultRow> {
        let mut rows = Vec::new();
        for season in 2020..=2024 {
            for idx in 0..4 {
                rows.push(LocalResultRow {
                    source_id: "local".to_string(),
                    competition_id: if idx % 2 == 0 { "eng".to_string() } else { "esp".to_string() },
                    season,
                    source_event_id: format!("{season}-{idx}"),
                    rating_diff: if idx % 2 == 0 { 0.25 } else { -0.10 },
                    form_diff: if idx % 3 == 0 { 0.10 } else { -0.05 },
                    rest_diff: 0.0,
                    home_score: if idx % 2 == 0 { 2 } else { 0 },
                    away_score: if idx % 2 == 0 { 1 } else { 1 },
                    payload_sha256: format!("hash-{season}-{idx}"),
                });
            }
        }
        rows.push(rows[0].clone());
        rows
    }

    #[test]
    fn parses_jsonl_rows() {
        let text = sample_rows()[..2]
            .iter()
            .map(|row| serde_json::to_string(row).unwrap())
            .collect::<Vec<_>>()
            .join("\n");
        let parsed = parse_result_rows_from_jsonl(&text).unwrap();
        assert_eq!(parsed.len(), 2);
    }

    #[test]
    fn builds_features_and_walk_forward_eval() {
        let (deduped, _) = dedupe_rows(&sample_rows());
        let training = build_training_rows(&deduped);
        let features = training_to_feature_rows(&training);
        let eval = walk_forward_predictions(&features, 2023);
        assert_eq!(features.len(), training.len());
        assert!(!eval.is_empty());
        assert!(eval.iter().all(|row| row.probability >= 0.02 && row.probability <= 0.98));
    }

    #[test]
    fn builds_runtime_report_and_bridge_payload() {
        let rows = sample_rows();
        let report = build_runtime_report(&rows, 2023);
        assert!(report.ok);
        assert_eq!(report.input_rows, 21);
        assert_eq!(report.deduped_rows, 20);
        assert!(report.evaluation_rows > 0);
        assert!(report.calibration_band_count > 0);
        assert_eq!(report.metrics_by_competition.len(), 2);
        let payload = build_runtime_bridge_payload(&rows, 2023);
        assert!(payload.ok);
        assert_eq!(payload.readiness.len(), 8);
    }
}
