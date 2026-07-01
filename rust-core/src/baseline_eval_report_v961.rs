use crate::FootballDataMatchRowV891;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineEvalConfigV961 {
    pub min_training_rows: usize,
    pub min_eval_rows: usize,
    pub eval_fraction: f64,
    pub source_label: String,
}

impl Default for BaselineEvalConfigV961 {
    fn default() -> Self {
        Self {
            min_training_rows: 200,
            min_eval_rows: 50,
            eval_fraction: 0.20,
            source_label: "canonical_matches".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineEvalMetricsV961 {
    pub market_family: String,
    pub market_scope: String,
    pub eval_rows: usize,
    pub accuracy: f64,
    pub log_loss: f64,
    pub brier_score: f64,
    pub calibration_ece: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CalibrationBinV961 {
    pub bin: usize,
    pub lower: f64,
    pub upper: f64,
    pub rows: usize,
    pub avg_confidence: f64,
    pub accuracy: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BaselineEvalReportV961 {
    pub schema: String,
    pub generated_by: String,
    pub source_label: String,
    pub input_rows: usize,
    pub parsed_rows: usize,
    pub eligible_rows: usize,
    pub train_rows: usize,
    pub eval_rows: usize,
    pub min_training_rows: usize,
    pub min_eval_rows: usize,
    pub eval_fraction: f64,
    pub ready: bool,
    pub status: String,
    pub baseline_training_allowed: bool,
    pub real_model_ready: bool,
    pub model_status: String,
    pub baseline_id: String,
    pub metrics: Option<BaselineEvalMetricsV961>,
    pub calibration_bins: Vec<CalibrationBinV961>,
    pub skipped_rows: Vec<String>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone)]
struct EvalPredictionV961 {
    confidence: f64,
    correct: bool,
    probs: [f64; 3],
    actual_idx: usize,
}

pub fn build_baseline_eval_report_v961(
    matches_jsonl: &str,
    config: &BaselineEvalConfigV961,
) -> Result<BaselineEvalReportV961, String> {
    let mut input_rows = 0usize;
    let mut parsed_rows = 0usize;
    let mut skipped_rows = Vec::new();
    let mut rows = Vec::new();

    for (idx, line) in matches_jsonl.lines().enumerate() {
        let line_number = idx + 1;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        input_rows += 1;
        match serde_json::from_str::<FootballDataMatchRowV891>(line) {
            Ok(row) => {
                parsed_rows += 1;
                if row.status.to_ascii_lowercase() != "final" {
                    skipped_rows.push(format!("line {line_number}: not_final_status:{}", row.status));
                    continue;
                }
                if result_index_v961(&row.full_time_result).is_none() {
                    skipped_rows.push(format!("line {line_number}: invalid_full_time_result:{}", row.full_time_result));
                    continue;
                }
                rows.push(row);
            }
            Err(err) => skipped_rows.push(format!("line {line_number}: invalid_json:{err}")),
        }
    }

    rows.sort_by(|a, b| {
        a.match_date
            .cmp(&b.match_date)
            .then(a.source_match_id.cmp(&b.source_match_id))
    });

    let eligible_rows = rows.len();
    if eligible_rows < config.min_training_rows + config.min_eval_rows {
        return Ok(blocked_report_v961(
            config,
            input_rows,
            parsed_rows,
            eligible_rows,
            skipped_rows,
        ));
    }

    let eval_fraction = if config.eval_fraction.is_finite() && config.eval_fraction > 0.0 && config.eval_fraction < 0.8 {
        config.eval_fraction
    } else {
        0.20
    };
    let requested_eval_rows = ((eligible_rows as f64) * eval_fraction).ceil() as usize;
    let eval_rows = requested_eval_rows
        .max(config.min_eval_rows)
        .min(eligible_rows - config.min_training_rows);
    let split_idx = eligible_rows - eval_rows;
    let train_rows = split_idx;

    let mut counts = [1usize, 1usize, 1usize];
    for row in &rows[..split_idx] {
        let idx = result_index_v961(&row.full_time_result).ok_or_else(|| "invalid training result after filtering".to_string())?;
        counts[idx] += 1;
    }

    let mut predictions = Vec::new();
    let mut correct = 0usize;
    let mut log_loss_sum = 0.0f64;
    let mut brier_sum = 0.0f64;

    for row in &rows[split_idx..] {
        let actual_idx = result_index_v961(&row.full_time_result).ok_or_else(|| "invalid eval result after filtering".to_string())?;
        let probs = probs_from_counts_v961(counts);
        let predicted_idx = argmax_v961(probs);
        let confidence = probs[predicted_idx];
        let is_correct = predicted_idx == actual_idx;
        if is_correct {
            correct += 1;
        }
        log_loss_sum += -probs[actual_idx].max(1e-15).ln();
        brier_sum += brier_v961(probs, actual_idx);
        predictions.push(EvalPredictionV961 {
            confidence,
            correct: is_correct,
            probs,
            actual_idx,
        });
        counts[actual_idx] += 1;
    }

    let eval_rows_f = eval_rows as f64;
    let accuracy = correct as f64 / eval_rows_f;
    let log_loss = log_loss_sum / eval_rows_f;
    let brier_score = brier_sum / eval_rows_f;
    let calibration_bins = calibration_bins_v961(&predictions, 5);
    let calibration_ece = calibration_ece_v961(&calibration_bins, eval_rows);

    Ok(BaselineEvalReportV961 {
        schema: "omnibet.baseline_eval_report.v961".to_string(),
        generated_by: "omnibet-baseline-eval".to_string(),
        source_label: config.source_label.clone(),
        input_rows,
        parsed_rows,
        eligible_rows,
        train_rows,
        eval_rows,
        min_training_rows: config.min_training_rows,
        min_eval_rows: config.min_eval_rows,
        eval_fraction,
        ready: true,
        status: "baseline_eval_complete".to_string(),
        baseline_training_allowed: true,
        real_model_ready: false,
        model_status: "baseline_eval_complete_stronger_model_required".to_string(),
        baseline_id: "chronological_expanding_frequency_1x2_v961".to_string(),
        metrics: Some(BaselineEvalMetricsV961 {
            market_family: "1x2".to_string(),
            market_scope: "regulation_90".to_string(),
            eval_rows,
            accuracy,
            log_loss,
            brier_score,
            calibration_ece,
        }),
        calibration_bins,
        skipped_rows,
        notes: vec![
            "This is a simple chronological expanding-frequency 1X2 baseline, not a trained betting model.".to_string(),
            "No random split is used; the last chronological slice is evaluation data.".to_string(),
            "real_model_ready remains false until stronger walk-forward evaluation, calibration, and market comparison gates pass.".to_string(),
            "No profit, staking, or betting advice claim is made by this report.".to_string(),
        ],
    })
}

pub fn write_baseline_eval_report_v961(report: &BaselineEvalReportV961, out_path: &Path) -> Result<(), String> {
    if let Some(parent) = out_path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
        }
    }
    let text = serde_json::to_string_pretty(report).map_err(|e| format!("serialize baseline eval report: {e}"))?;
    fs::write(out_path, format!("{text}\n")).map_err(|e| format!("write {}: {e}", out_path.display()))
}

fn blocked_report_v961(
    config: &BaselineEvalConfigV961,
    input_rows: usize,
    parsed_rows: usize,
    eligible_rows: usize,
    skipped_rows: Vec<String>,
) -> BaselineEvalReportV961 {
    BaselineEvalReportV961 {
        schema: "omnibet.baseline_eval_report.v961".to_string(),
        generated_by: "omnibet-baseline-eval".to_string(),
        source_label: config.source_label.clone(),
        input_rows,
        parsed_rows,
        eligible_rows,
        train_rows: 0,
        eval_rows: 0,
        min_training_rows: config.min_training_rows,
        min_eval_rows: config.min_eval_rows,
        eval_fraction: config.eval_fraction,
        ready: false,
        status: "blocked_insufficient_rows".to_string(),
        baseline_training_allowed: false,
        real_model_ready: false,
        model_status: "locked_needs_more_rows_for_eval".to_string(),
        baseline_id: "chronological_expanding_frequency_1x2_v961".to_string(),
        metrics: None,
        calibration_bins: Vec::new(),
        skipped_rows,
        notes: vec![
            format!(
                "Need at least {} eligible rows: {} training rows + {} eval rows.",
                config.min_training_rows + config.min_eval_rows,
                config.min_training_rows,
                config.min_eval_rows
            ),
            "This blocked report is intentional and prevents fake model readiness.".to_string(),
        ],
    }
}

fn result_index_v961(result: &str) -> Option<usize> {
    match result {
        "H" | "home" => Some(0),
        "D" | "draw" => Some(1),
        "A" | "away" => Some(2),
        _ => None,
    }
}

fn probs_from_counts_v961(counts: [usize; 3]) -> [f64; 3] {
    let total = counts.iter().sum::<usize>() as f64;
    [
        counts[0] as f64 / total,
        counts[1] as f64 / total,
        counts[2] as f64 / total,
    ]
}

fn argmax_v961(probs: [f64; 3]) -> usize {
    let mut best_idx = 0usize;
    let mut best_value = probs[0];
    for (idx, value) in probs.iter().enumerate().skip(1) {
        if *value > best_value {
            best_idx = idx;
            best_value = *value;
        }
    }
    best_idx
}

fn brier_v961(probs: [f64; 3], actual_idx: usize) -> f64 {
    let mut total = 0.0;
    for (idx, prob) in probs.iter().enumerate() {
        let target = if idx == actual_idx { 1.0 } else { 0.0 };
        total += (prob - target) * (prob - target);
    }
    total
}

fn calibration_bins_v961(predictions: &[EvalPredictionV961], bins: usize) -> Vec<CalibrationBinV961> {
    let mut rows = vec![0usize; bins];
    let mut conf_sum = vec![0.0f64; bins];
    let mut correct_sum = vec![0usize; bins];
    for prediction in predictions {
        let mut idx = (prediction.confidence * bins as f64).floor() as usize;
        if idx >= bins {
            idx = bins - 1;
        }
        rows[idx] += 1;
        conf_sum[idx] += prediction.confidence;
        if prediction.correct {
            correct_sum[idx] += 1;
        }
    }
    (0..bins)
        .map(|idx| {
            let count = rows[idx];
            CalibrationBinV961 {
                bin: idx,
                lower: idx as f64 / bins as f64,
                upper: (idx + 1) as f64 / bins as f64,
                rows: count,
                avg_confidence: if count == 0 { 0.0 } else { conf_sum[idx] / count as f64 },
                accuracy: if count == 0 { 0.0 } else { correct_sum[idx] as f64 / count as f64 },
            }
        })
        .collect()
}

fn calibration_ece_v961(bins: &[CalibrationBinV961], eval_rows: usize) -> f64 {
    if eval_rows == 0 {
        return 0.0;
    }
    bins.iter()
        .map(|bin| (bin.rows as f64 / eval_rows as f64) * (bin.avg_confidence - bin.accuracy).abs())
        .sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn row(idx: usize, result: &str) -> String {
        let day = (idx % 28) + 1;
        format!(
            "{{\"schema\":\"omnibet.football_data_match_row.v891\",\"source_id\":\"test\",\"competition_id\":\"test_league\",\"season_id\":\"2024_2025\",\"source_match_id\":\"m{idx}\",\"match_date\":\"2024-08-{day:02}\",\"kickoff_time\":null,\"home_team_raw\":\"Home{idx}\",\"away_team_raw\":\"Away{idx}\",\"final_home_goals\":1,\"final_away_goals\":0,\"full_time_result\":\"{result}\",\"half_time_home_goals\":null,\"half_time_away_goals\":null,\"half_time_result\":null,\"status\":\"final\",\"payload_sha256\":\"sha{idx}\"}}\n"
        )
    }

    #[test]
    fn blocks_when_rows_are_insufficient() {
        let jsonl = format!("{}{}{}", row(1, "H"), row(2, "D"), row(3, "A"));
        let report = build_baseline_eval_report_v961(&jsonl, &BaselineEvalConfigV961::default()).expect("blocked report");
        assert!(!report.ready);
        assert_eq!(report.status, "blocked_insufficient_rows");
        assert!(report.metrics.is_none());
        assert!(!report.real_model_ready);
    }

    #[test]
    fn evaluates_chronological_frequency_baseline() {
        let mut jsonl = String::new();
        for idx in 0..30 {
            let result = if idx % 3 == 0 { "H" } else if idx % 3 == 1 { "D" } else { "A" };
            jsonl.push_str(&row(idx, result));
        }
        let config = BaselineEvalConfigV961 {
            min_training_rows: 20,
            min_eval_rows: 5,
            eval_fraction: 0.20,
            source_label: "test".to_string(),
        };
        let report = build_baseline_eval_report_v961(&jsonl, &config).expect("eval report");
        assert!(report.ready);
        assert_eq!(report.train_rows, 24);
        assert_eq!(report.eval_rows, 6);
        assert_eq!(report.status, "baseline_eval_complete");
        assert!(report.metrics.is_some());
        assert_eq!(report.calibration_bins.len(), 5);
        assert!(!report.real_model_ready);
    }
}
