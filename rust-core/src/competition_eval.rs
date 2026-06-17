use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CompetitionIdentity {
    pub competition_id: String,
    pub name: String,
    pub country: String,
    pub tier: u32,
    pub train_separately: bool,
    pub calibrate_separately: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LeagueMetricRow {
    pub competition_id: String,
    pub model_id: String,
    pub rows: usize,
    pub brier: f64,
    pub logloss: f64,
    pub accuracy_at_0_5: f64,
    pub calibration_ece: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LeagueCalibrationBin {
    pub competition_id: String,
    pub bin: String,
    pub rows: usize,
    pub avg_probability: Option<f64>,
    pub observed_rate: Option<f64>,
    pub gap: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CompetitionPredictionRow {
    pub competition_id: String,
    pub model_id: String,
    pub label_home_win: u8,
    pub probability: f64,
}

pub fn clamp_probability(p: f64) -> f64 {
    p.clamp(0.02, 0.98)
}

pub fn brier_score(rows: &[CompetitionPredictionRow]) -> f64 {
    if rows.is_empty() {
        return 0.0;
    }
    rows.iter()
        .map(|row| {
            let y = row.label_home_win as f64;
            let p = clamp_probability(row.probability);
            (p - y) * (p - y)
        })
        .sum::<f64>()
        / rows.len() as f64
}

pub fn log_loss(rows: &[CompetitionPredictionRow]) -> f64 {
    if rows.is_empty() {
        return 0.0;
    }
    rows.iter()
        .map(|row| {
            let y = row.label_home_win as f64;
            let p = clamp_probability(row.probability);
            -(y * p.ln() + (1.0 - y) * (1.0 - p).ln())
        })
        .sum::<f64>()
        / rows.len() as f64
}

pub fn accuracy_at_half(rows: &[CompetitionPredictionRow]) -> f64 {
    if rows.is_empty() {
        return 0.0;
    }
    rows.iter()
        .filter(|row| (row.probability >= 0.5) == (row.label_home_win == 1))
        .count() as f64
        / rows.len() as f64
}

pub fn metric_by_competition(rows: &[CompetitionPredictionRow]) -> Vec<LeagueMetricRow> {
    let mut groups: BTreeMap<(String, String), Vec<CompetitionPredictionRow>> = BTreeMap::new();
    for row in rows {
        groups
            .entry((row.competition_id.clone(), row.model_id.clone()))
            .or_default()
            .push(row.clone());
    }
    groups
        .into_iter()
        .map(|((competition_id, model_id), group)| LeagueMetricRow {
            competition_id,
            model_id,
            rows: group.len(),
            brier: brier_score(&group),
            logloss: log_loss(&group),
            accuracy_at_0_5: accuracy_at_half(&group),
            calibration_ece: 0.0,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn computes_basic_metrics() {
        let rows = vec![
            CompetitionPredictionRow { competition_id: "eng".into(), model_id: "m".into(), label_home_win: 1, probability: 0.7 },
            CompetitionPredictionRow { competition_id: "eng".into(), model_id: "m".into(), label_home_win: 0, probability: 0.4 },
        ];
        assert!(brier_score(&rows) > 0.0);
        assert!(log_loss(&rows) > 0.0);
        assert_eq!(accuracy_at_half(&rows), 1.0);
        assert_eq!(metric_by_competition(&rows).len(), 1);
    }
}
