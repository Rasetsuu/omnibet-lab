use crate::typed_rows::{parse_feature_json, read_gold_match_features, GoldMatchFeatureRow};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
pub struct FeatureSpec {
    pub name: String,
    pub path: String,
    pub fallback_home: Option<String>,
    pub fallback_away: Option<String>,
    pub default: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Calibration {
    pub shrink_alpha: f64,
    pub base_probs: [f64; 3],
}

#[derive(Debug, Clone, Deserialize)]
pub struct LinearModel {
    pub name: String,
    pub version: String,
    pub sport: String,
    pub model_trust: f64,
    pub classes: [String; 3],
    pub intercept: [f64; 3],
    pub features: Vec<FeatureSpec>,
    pub weights: Vec<[f64; 3]>,
    pub calibration: Calibration,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LinearModelRow {
    pub match_id: String,
    pub match_date: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub actual: String,
    pub pick: String,
    pub probs: [f64; 3],
    pub log_loss: f64,
    pub brier: f64,
    pub feature_values: Vec<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct LinearModelBacktest {
    pub ok: bool,
    pub model_name: String,
    pub model_version: String,
    pub model_trust: f64,
    pub rows_total: usize,
    pub rows_tested: usize,
    pub min_train: usize,
    pub accuracy: f64,
    pub log_loss: f64,
    pub brier: f64,
    pub trust_decision: String,
    pub notes: String,
    pub samples: Vec<LinearModelRow>,
}

pub fn load_linear_model(path: &Path) -> Result<LinearModel, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("failed to read model {}: {}", path.display(), e))?;
    let model: LinearModel = serde_json::from_str(&text).map_err(|e| format!("failed to parse model JSON: {}", e))?;
    if model.features.len() != model.weights.len() {
        return Err(format!("feature/weight length mismatch: {} vs {}", model.features.len(), model.weights.len()));
    }
    Ok(model)
}

fn value_at(root: &Value, path: &str) -> Option<f64> {
    let mut cur = root;
    for part in path.split('.') {
        cur = cur.get(part)?;
    }
    cur.as_f64()
}

fn feature_value(root: &Value, spec: &FeatureSpec) -> f64 {
    if let Some(v) = value_at(root, &spec.path) {
        return v;
    }
    if let (Some(hp), Some(ap)) = (&spec.fallback_home, &spec.fallback_away) {
        let h = value_at(root, hp);
        let a = value_at(root, ap);
        match (h, a) {
            (Some(hv), Some(av)) => return hv - av,
            (Some(hv), None) => return hv,
            (None, Some(av)) => return -av,
            _ => {}
        }
    }
    spec.default
}

fn softmax3(logits: [f64; 3]) -> [f64; 3] {
    let m = logits[0].max(logits[1]).max(logits[2]);
    let e0 = (logits[0] - m).exp();
    let e1 = (logits[1] - m).exp();
    let e2 = (logits[2] - m).exp();
    let s = e0 + e1 + e2;
    [e0 / s, e1 / s, e2 / s]
}

fn apply_calibration(mut probs: [f64; 3], calibration: &Calibration) -> [f64; 3] {
    let a = calibration.shrink_alpha.clamp(0.0, 1.0);
    for i in 0..3 {
        probs[i] = (1.0 - a) * probs[i] + a * calibration.base_probs[i];
    }
    let s = probs[0] + probs[1] + probs[2];
    if s > 0.0 {
        for p in &mut probs {
            *p /= s;
        }
    }
    probs
}

pub fn predict_row(model: &LinearModel, row: &GoldMatchFeatureRow) -> Result<([f64; 3], Vec<f64>), String> {
    let root = parse_feature_json(row)?;
    let values: Vec<f64> = model.features.iter().map(|spec| feature_value(&root, spec)).collect();
    let mut logits = model.intercept;
    for (idx, v) in values.iter().enumerate() {
        for class_idx in 0..3 {
            logits[class_idx] += v * model.weights[idx][class_idx];
        }
    }
    Ok((apply_calibration(softmax3(logits), &model.calibration), values))
}

fn actual(row: &GoldMatchFeatureRow) -> Option<String> {
    let h = row.target_home_goals?;
    let a = row.target_away_goals?;
    if h > a {
        Some("H".to_string())
    } else if h < a {
        Some("A".to_string())
    } else {
        Some("D".to_string())
    }
}

fn class_index(class_name: &str) -> Option<usize> {
    match class_name {
        "H" => Some(0),
        "D" => Some(1),
        "A" => Some(2),
        _ => None,
    }
}

fn pick(probs: [f64; 3]) -> String {
    let mut best = 0;
    for i in 1..3 {
        if probs[i] > probs[best] {
            best = i;
        }
    }
    ["H", "D", "A"][best].to_string()
}

fn log_loss(probs: [f64; 3], actual: &str) -> f64 {
    let idx = class_index(actual).unwrap_or(0);
    -probs[idx].max(1e-12).ln()
}

fn brier(probs: [f64; 3], actual: &str) -> f64 {
    let idx = class_index(actual).unwrap_or(0);
    let mut out = 0.0;
    for i in 0..3 {
        let t = if i == idx { 1.0 } else { 0.0 };
        out += (probs[i] - t).powi(2);
    }
    out
}

pub fn backtest_linear_model(pack_dir: &Path, model_path: &Path, min_train: usize, include_rows: bool) -> Result<LinearModelBacktest, String> {
    let model = load_linear_model(model_path)?;
    let mut rows = read_gold_match_features(pack_dir, 2_000_000)?;
    rows.sort_by(|a, b| {
        a.match_date.clone().unwrap_or_default().cmp(&b.match_date.clone().unwrap_or_default())
            .then(a.match_id.cmp(&b.match_id))
    });

    let mut tested = Vec::new();
    for (idx, row) in rows.iter().enumerate() {
        if idx < min_train {
            continue;
        }
        let Some(act) = actual(row) else { continue; };
        let (probs, values) = predict_row(&model, row)?;
        tested.push(LinearModelRow {
            match_id: row.match_id.clone(),
            match_date: row.match_date.clone(),
            home_team: row.home_team_name.clone(),
            away_team: row.away_team_name.clone(),
            actual: act.clone(),
            pick: pick(probs),
            probs,
            log_loss: log_loss(probs, &act),
            brier: brier(probs, &act),
            feature_values: values,
        });
    }

    let denom = tested.len().max(1) as f64;
    let accuracy = tested.iter().filter(|r| r.pick == r.actual).count() as f64 / denom;
    let ll = tested.iter().map(|r| r.log_loss).sum::<f64>() / denom;
    let br = tested.iter().map(|r| r.brier).sum::<f64>() / denom;
    let samples = if include_rows { tested.clone() } else { tested.iter().take(8).cloned().collect() };

    Ok(LinearModelBacktest {
        ok: !tested.is_empty(),
        model_name: model.name,
        model_version: model.version,
        model_trust: model.model_trust,
        rows_total: rows.len(),
        rows_tested: tested.len(),
        min_train,
        accuracy,
        log_loss: ll,
        brier: br,
        trust_decision: if model.model_trust < 0.50 { "PAPER_ONLY" } else { "TRUSTED_FOR_STAKING_LABELS" }.to_string(),
        notes: model.notes.unwrap_or_else(|| "Linear model runtime".to_string()),
        samples,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn softmax_sums_to_one() {
        let p = softmax3([1.0, 0.0, -1.0]);
        let s = p[0] + p[1] + p[2];
        assert!((s - 1.0).abs() < 1e-12);
    }

    #[test]
    fn calibration_preserves_sum() {
        let c = Calibration { shrink_alpha: 0.2, base_probs: [0.4, 0.3, 0.3] };
        let p = apply_calibration([0.8, 0.1, 0.1], &c);
        let s = p[0] + p[1] + p[2];
        assert!((s - 1.0).abs() < 1e-12);
    }
}
