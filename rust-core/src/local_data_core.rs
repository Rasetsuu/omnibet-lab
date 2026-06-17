use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalResultRow {
    pub source_id: String,
    pub competition_id: String,
    pub season: i32,
    pub source_event_id: String,
    pub rating_diff: f64,
    pub form_diff: f64,
    pub rest_diff: f64,
    pub home_score: i32,
    pub away_score: i32,
    pub payload_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalTrainingRow {
    pub competition_id: String,
    pub season: i32,
    pub source_event_id: String,
    pub rating_diff: f64,
    pub form_diff: f64,
    pub rest_diff: f64,
    pub label_home_win: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LocalPredictionRow {
    pub competition_id: String,
    pub probability: f64,
    pub label_home_win: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct IntegrityReport {
    pub input_rows: usize,
    pub deduped_rows: usize,
    pub duplicate_rows: Vec<String>,
    pub missing_hash_rows: Vec<String>,
    pub ok: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MetricReport {
    pub rows: usize,
    pub brier: f64,
    pub accuracy_at_0_5: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CalibrationBand {
    pub bin: String,
    pub rows: usize,
    pub avg_probability: f64,
    pub observed_rate: f64,
    pub lower_95: f64,
    pub upper_95: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CoverageReport {
    pub covered_competitions: Vec<String>,
    pub covered_count: usize,
    pub min_season: i32,
    pub max_season: i32,
}

pub fn clamp_probability(p: f64) -> f64 {
    p.clamp(0.02, 0.98)
}

pub fn dedupe_rows(rows: &[LocalResultRow]) -> (Vec<LocalResultRow>, IntegrityReport) {
    let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
    let mut out = Vec::new();
    let mut duplicate_rows = Vec::new();
    let mut missing_hash_rows = Vec::new();
    for row in rows {
        let key = (row.source_id.clone(), row.source_event_id.clone());
        if row.payload_sha256.trim().is_empty() {
            missing_hash_rows.push(row.source_event_id.clone());
        }
        if seen.contains(&key) {
            duplicate_rows.push(row.source_event_id.clone());
            continue;
        }
        seen.insert(key);
        out.push(row.clone());
    }
    let report = IntegrityReport {
        input_rows: rows.len(),
        deduped_rows: out.len(),
        ok: missing_hash_rows.is_empty(),
        duplicate_rows,
        missing_hash_rows,
    };
    (out, report)
}

pub fn build_training_rows(rows: &[LocalResultRow]) -> Vec<LocalTrainingRow> {
    rows.iter()
        .map(|row| LocalTrainingRow {
            competition_id: row.competition_id.clone(),
            season: row.season,
            source_event_id: row.source_event_id.clone(),
            rating_diff: row.rating_diff,
            form_diff: row.form_diff,
            rest_diff: row.rest_diff,
            label_home_win: u8::from(row.home_score > row.away_score),
        })
        .collect()
}

pub fn brier_score(rows: &[LocalPredictionRow]) -> f64 {
    if rows.is_empty() {
        return 0.0;
    }
    rows.iter()
        .map(|row| {
            let p = clamp_probability(row.probability);
            let y = row.label_home_win as f64;
            (p - y) * (p - y)
        })
        .sum::<f64>()
        / rows.len() as f64
}

pub fn accuracy_at_half(rows: &[LocalPredictionRow]) -> f64 {
    if rows.is_empty() {
        return 0.0;
    }
    rows.iter()
        .filter(|row| (row.probability >= 0.5) == (row.label_home_win == 1))
        .count() as f64
        / rows.len() as f64
}

pub fn metric_report(rows: &[LocalPredictionRow]) -> MetricReport {
    MetricReport {
        rows: rows.len(),
        brier: brier_score(rows),
        accuracy_at_0_5: accuracy_at_half(rows),
    }
}

pub fn calibration_bands(rows: &[LocalPredictionRow]) -> Vec<CalibrationBand> {
    let mut out = Vec::new();
    for (lo, hi) in [(0.0, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.0)] {
        let bin_rows: Vec<&LocalPredictionRow> = rows
            .iter()
            .filter(|row| (row.probability >= lo && row.probability < hi) || (hi >= 1.0 && row.probability <= hi))
            .collect();
        if bin_rows.is_empty() {
            continue;
        }
        let n = bin_rows.len() as f64;
        let avg_probability = bin_rows.iter().map(|row| row.probability).sum::<f64>() / n;
        let observed_rate = bin_rows.iter().map(|row| row.label_home_win as f64).sum::<f64>() / n;
        let margin = 1.96 * ((observed_rate * (1.0 - observed_rate)).max(0.0001) / n).sqrt();
        out.push(CalibrationBand {
            bin: format!("{lo:.2}-{hi:.2}"),
            rows: bin_rows.len(),
            avg_probability,
            observed_rate,
            lower_95: (observed_rate - margin).max(0.0),
            upper_95: (observed_rate + margin).min(1.0),
        });
    }
    out
}

pub fn coverage_report(rows: &[LocalTrainingRow]) -> CoverageReport {
    let mut comps = BTreeSet::new();
    let mut min_season = i32::MAX;
    let mut max_season = i32::MIN;
    for row in rows {
        comps.insert(row.competition_id.clone());
        min_season = min_season.min(row.season);
        max_season = max_season.max(row.season);
    }
    CoverageReport {
        covered_competitions: comps.into_iter().collect(),
        covered_count: rows.iter().map(|r| r.competition_id.clone()).collect::<BTreeSet<_>>().len(),
        min_season: if rows.is_empty() { 0 } else { min_season },
        max_season: if rows.is_empty() { 0 } else { max_season },
    }
}

pub fn metrics_by_competition(rows: &[LocalPredictionRow]) -> BTreeMap<String, MetricReport> {
    let mut groups: BTreeMap<String, Vec<LocalPredictionRow>> = BTreeMap::new();
    for row in rows {
        groups.entry(row.competition_id.clone()).or_default().push(row.clone());
    }
    groups.into_iter().map(|(key, value)| (key, metric_report(&value))).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_rows() -> Vec<LocalResultRow> {
        vec![
            LocalResultRow { source_id: "s".into(), competition_id: "eng".into(), season: 2024, source_event_id: "a".into(), rating_diff: 0.2, form_diff: 0.1, rest_diff: 0.0, home_score: 2, away_score: 1, payload_sha256: "hash-a".into() },
            LocalResultRow { source_id: "s".into(), competition_id: "eng".into(), season: 2024, source_event_id: "a".into(), rating_diff: 0.2, form_diff: 0.1, rest_diff: 0.0, home_score: 2, away_score: 1, payload_sha256: "hash-a".into() },
            LocalResultRow { source_id: "s".into(), competition_id: "esp".into(), season: 2025, source_event_id: "b".into(), rating_diff: -0.1, form_diff: 0.0, rest_diff: 0.2, home_score: 0, away_score: 1, payload_sha256: "hash-b".into() },
        ]
    }

    #[test]
    fn dedupes_and_builds_training_rows() {
        let (deduped, report) = dedupe_rows(&sample_rows());
        assert_eq!(deduped.len(), 2);
        assert_eq!(report.duplicate_rows.len(), 1);
        let train = build_training_rows(&deduped);
        assert_eq!(train.len(), 2);
        assert_eq!(train[0].label_home_win, 1);
        assert_eq!(train[1].label_home_win, 0);
    }

    #[test]
    fn computes_metrics_calibration_and_coverage() {
        let preds = vec![
            LocalPredictionRow { competition_id: "eng".into(), probability: 0.7, label_home_win: 1 },
            LocalPredictionRow { competition_id: "eng".into(), probability: 0.4, label_home_win: 0 },
            LocalPredictionRow { competition_id: "esp".into(), probability: 0.6, label_home_win: 1 },
        ];
        assert!(brier_score(&preds) > 0.0);
        assert!(accuracy_at_half(&preds) > 0.9);
        assert!(!calibration_bands(&preds).is_empty());
        assert_eq!(metrics_by_competition(&preds).len(), 2);
        let train = build_training_rows(&dedupe_rows(&sample_rows()).0);
        let coverage = coverage_report(&train);
        assert_eq!(coverage.covered_count, 2);
        assert_eq!(coverage.min_season, 2024);
        assert_eq!(coverage.max_season, 2025);
    }
}
