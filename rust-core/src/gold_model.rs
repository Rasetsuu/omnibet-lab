use crate::inference::{BacktestRow, BacktestSummary, OutcomeProbabilities};
use crate::typed_rows::{parse_feature_json, read_gold_match_features, GoldMatchFeatureRow};
use serde::Serialize;
use serde_json::Value;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct ModelComparison {
    pub ok: bool,
    pub baseline: BacktestSummary,
    pub gold_feature_heuristic: BacktestSummary,
    pub min_train: usize,
    pub aligned_test_window: bool,
    pub note: String,
}

fn sigmoid(x: f64) -> f64 {
    // Numerically stable sigmoid, clipped away from exact 0/1 so tests
    // and downstream log-loss calculations avoid saturated probabilities.
    let y = if x >= 0.0 {
        let z = (-x).exp();
        1.0 / (1.0 + z)
    } else {
        let z = x.exp();
        z / (1.0 + z)
    };
    y.clamp(1e-12, 1.0 - 1e-12)
}

fn softmax3(h: f64, d: f64, a: f64) -> OutcomeProbabilities {
    let m = h.max(d).max(a);
    let eh = (h - m).exp();
    let ed = (d - m).exp();
    let ea = (a - m).exp();
    let s = eh + ed + ea;
    OutcomeProbabilities {
        home: eh / s,
        draw: ed / s,
        away: ea / s,
    }
}

fn actual_outcome(home: i32, away: i32) -> String {
    if home > away {
        "H".to_string()
    } else if home < away {
        "A".to_string()
    } else {
        "D".to_string()
    }
}

fn pick_from_probs(p: &OutcomeProbabilities) -> String {
    if p.home >= p.draw && p.home >= p.away {
        "H".to_string()
    } else if p.away >= p.home && p.away >= p.draw {
        "A".to_string()
    } else {
        "D".to_string()
    }
}

fn log_loss(p: &OutcomeProbabilities, actual: &str) -> f64 {
    let x = match actual {
        "H" => p.home,
        "D" => p.draw,
        "A" => p.away,
        _ => 1e-12,
    }
    .clamp(1e-12, 1.0);
    -x.ln()
}

fn brier(p: &OutcomeProbabilities, actual: &str) -> f64 {
    let h = if actual == "H" { 1.0 } else { 0.0 };
    let d = if actual == "D" { 1.0 } else { 0.0 };
    let a = if actual == "A" { 1.0 } else { 0.0 };
    (p.home - h).powi(2) + (p.draw - d).powi(2) + (p.away - a).powi(2)
}

fn num_at(v: &Value, ptr: &str, default: f64) -> f64 {
    v.pointer(ptr).and_then(|x| x.as_f64()).unwrap_or(default)
}

fn bool_at(v: &Value, ptr: &str, default: bool) -> bool {
    v.pointer(ptr).and_then(|x| x.as_bool()).unwrap_or(default)
}

fn gold_probabilities(row: &GoldMatchFeatureRow, f: &Value) -> (OutcomeProbabilities, f64, f64) {
    // Feature JSON is leakage-safe because it was built before the match result
    // was inserted into team histories.
    let home_prior = num_at(f, "/features/home_prior_matches", 0.0);
    let away_prior = num_at(f, "/features/away_prior_matches", 0.0);
    let min_prior = home_prior.min(away_prior);
    let reliability = (min_prior / 10.0).clamp(0.0, 1.0);

    let gf_diff = num_at(f, "/features/goals_for_avg_diff", 0.0);
    let ga_diff = num_at(f, "/features/goals_against_avg_diff", 0.0);
    let points_diff = num_at(f, "/features/points_avg_diff", 0.0);
    let rest_diff = num_at(f, "/features/rest_days_diff", 0.0).clamp(-14.0, 14.0);

    let has_event_data = bool_at(f, "/features/has_event_data", false);
    let xg_for_diff = num_at(f, "/features/xg_for_avg_diff", 0.0);
    let xg_against_diff = num_at(f, "/features/xg_against_avg_diff", 0.0);
    let shots_for_diff = num_at(f, "/features/shots_for_avg_diff", 0.0);

    let event_bonus = if has_event_data {
        0.25 * xg_for_diff - 0.18 * xg_against_diff + 0.015 * shots_for_diff
    } else {
        0.0
    };

    // Small home advantage plus reliability-weighted rolling-feature signal.
    let strength = 0.18
        + reliability
            * (0.42 * gf_diff
                - 0.30 * ga_diff
                + 0.16 * points_diff
                + 0.015 * rest_diff
                + event_bonus);

    // Draw probability increases when teams look close and data reliability is low.
    let draw_raw = -0.12 - 0.28 * strength.abs() + 0.08 * (1.0 - reliability);
    let probs = softmax3(strength, draw_raw, -strength);

    // Goals and BTTS use absolute team rolling rates when available.
    let home_gf = num_at(f, "/home_snapshot/goals_for_avg", 1.20);
    let away_gf = num_at(f, "/away_snapshot/goals_for_avg", 1.05);
    let home_ga = num_at(f, "/home_snapshot/goals_against_avg", 1.10);
    let away_ga = num_at(f, "/away_snapshot/goals_against_avg", 1.20);

    let expected_total = ((home_gf + away_ga) / 2.0 + (away_gf + home_ga) / 2.0).clamp(0.5, 5.5);
    let over25 = sigmoid(-0.22 + 0.55 * (expected_total - 2.50));
    let btts = sigmoid(-0.18 + 0.45 * (expected_total - 2.35) - 0.18 * strength.abs());

    // Early matches with no prior data should be pulled back toward base rates.
    let over25 = reliability * over25 + (1.0 - reliability) * 0.52;
    let btts = reliability * btts + (1.0 - reliability) * 0.50;

    let _ = row; // keep signature future-proof without warnings.

    (probs, over25, btts)
}

fn sort_gold_rows(rows: &mut [GoldMatchFeatureRow]) {
    rows.sort_by(|a, b| {
        let da = a.match_date.clone().unwrap_or_default();
        let db = b.match_date.clone().unwrap_or_default();
        da.cmp(&db).then(a.match_id.cmp(&b.match_id))
    });
}

fn evaluate_rows(mut rows: Vec<GoldMatchFeatureRow>, min_train: usize, include_rows: bool) -> BacktestSummary {
    sort_gold_rows(&mut rows);

    let mut tested = Vec::new();
    let total_rows = rows.len();

    for (idx, row) in rows.into_iter().enumerate() {
        if idx < min_train {
            continue;
        }

        let (Some(hg), Some(ag)) = (row.target_home_goals, row.target_away_goals) else {
            continue;
        };
        let Ok(f) = parse_feature_json(&row) else {
            continue;
        };
        let (probs, over25, btts_prob) = gold_probabilities(&row, &f);
        let actual = actual_outcome(hg, ag);
        let pick = pick_from_probs(&probs);
        let actual_over25 = hg + ag >= 3;
        let actual_btts = hg > 0 && ag > 0;

        tested.push(BacktestRow {
            match_id: row.match_id.clone(),
            match_date: row.match_date.clone(),
            home_team: row.home_team_name.clone(),
            away_team: row.away_team_name.clone(),
            actual_home_goals: hg,
            actual_away_goals: ag,
            actual_outcome: actual.clone(),
            predicted_pick: pick,
            home_prob: probs.home,
            draw_prob: probs.draw,
            away_prob: probs.away,
            over_25_prob: over25,
            actual_over_25: actual_over25,
            btts_prob,
            actual_btts,
            log_loss: log_loss(&probs, &actual),
            brier: brier(&probs, &actual),
        });
    }

    let n = tested.len().max(1) as f64;
    let acc = tested.iter().filter(|r| r.predicted_pick == r.actual_outcome).count() as f64 / n;
    let over_acc = tested.iter().filter(|r| (r.over_25_prob >= 0.5) == r.actual_over_25).count() as f64 / n;
    let btts_acc = tested.iter().filter(|r| (r.btts_prob >= 0.5) == r.actual_btts).count() as f64 / n;
    let ll = tested.iter().map(|r| r.log_loss).sum::<f64>() / n;
    let br = tested.iter().map(|r| r.brier).sum::<f64>() / n;

    let out_rows = if include_rows { tested } else { Vec::new() };

    BacktestSummary {
        ok: true,
        matches_total: total_rows,
        matches_tested: n as usize,
        min_train,
        one_x_two_accuracy: acc,
        over_25_accuracy: over_acc,
        btts_accuracy: btts_acc,
        log_loss: ll,
        brier: br,
        rows: out_rows,
        note: "v11 Rust gold-feature heuristic over leakage-safe gold_match_features. Test window is now aligned by min_train.".to_string(),
    }
}

pub fn backtest_gold_from_pack(pack_dir: &Path, min_train: usize, include_rows: bool) -> Result<BacktestSummary, String> {
    let rows = read_gold_match_features(pack_dir, 2_000_000)?;
    Ok(evaluate_rows(rows, min_train, include_rows))
}

pub fn compare_models_from_pack(pack_dir: &Path, min_train: usize) -> Result<ModelComparison, String> {
    let baseline = crate::inference::backtest_from_pack(pack_dir, min_train, false)?;
    let gold_feature_heuristic = backtest_gold_from_pack(pack_dir, min_train, false)?;
    let aligned = baseline.matches_tested == gold_feature_heuristic.matches_tested;

    Ok(ModelComparison {
        ok: true,
        baseline,
        gold_feature_heuristic,
        min_train,
        aligned_test_window: aligned,
        note: "v11 comparison uses the same min_train/test-window for baseline and gold-feature heuristic.".to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn softmax_sums_to_one() {
        let p = softmax3(0.2, -0.1, -0.2);
        let s = p.home + p.draw + p.away;
        assert!((s - 1.0).abs() < 1e-12);
    }

    #[test]
    fn sigmoid_bounds() {
        assert!(sigmoid(-100.0) > 0.0);
        assert!(sigmoid(100.0) < 1.0);
    }
}
