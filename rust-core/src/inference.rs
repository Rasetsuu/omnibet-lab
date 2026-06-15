use crate::odds::fair_odds;
use crate::typed_rows::{read_matches, MatchNormRow};
use serde::Serialize;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Default)]
struct TeamAgg {
    matches: u32,
    goals_for: f64,
    goals_against: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct OutcomeProbabilities {
    pub home: f64,
    pub draw: f64,
    pub away: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct SimplePrediction {
    pub home_team: String,
    pub away_team: String,
    pub lambda_home: f64,
    pub lambda_away: f64,
    pub outcome: OutcomeProbabilities,
    pub over_25: f64,
    pub btts: f64,
    pub most_likely_score: (u32, u32),
    pub fair_odds_home: f64,
    pub fair_odds_draw: f64,
    pub fair_odds_away: f64,
    pub training_matches: usize,
    pub note: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct BacktestRow {
    pub match_id: String,
    pub match_date: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub actual_home_goals: i32,
    pub actual_away_goals: i32,
    pub actual_outcome: String,
    pub predicted_pick: String,
    pub home_prob: f64,
    pub draw_prob: f64,
    pub away_prob: f64,
    pub over_25_prob: f64,
    pub actual_over_25: bool,
    pub btts_prob: f64,
    pub actual_btts: bool,
    pub log_loss: f64,
    pub brier: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BacktestSummary {
    pub ok: bool,
    pub matches_total: usize,
    pub matches_tested: usize,
    pub min_train: usize,
    pub one_x_two_accuracy: f64,
    pub over_25_accuracy: f64,
    pub btts_accuracy: f64,
    pub log_loss: f64,
    pub brier: f64,
    pub rows: Vec<BacktestRow>,
    pub note: String,
}

fn canonical(s: &str) -> String {
    s.trim().to_lowercase()
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

fn poisson_pmf(k: u32, lambda: f64) -> f64 {
    let lam = lambda.max(1e-9);
    let mut out = (-lam).exp();
    for i in 0..k {
        out *= lam / ((i + 1) as f64);
    }
    out
}

fn score_matrix(lambda_home: f64, lambda_away: f64, max_goals: u32) -> Vec<Vec<f64>> {
    let n = max_goals as usize + 1;
    let mut mat = vec![vec![0.0; n]; n];
    let mut total = 0.0;
    for i in 0..=max_goals {
        for j in 0..=max_goals {
            let p = poisson_pmf(i, lambda_home) * poisson_pmf(j, lambda_away);
            mat[i as usize][j as usize] = p;
            total += p;
        }
    }
    if total > 0.0 {
        for row in &mut mat {
            for p in row {
                *p /= total;
            }
        }
    }
    mat
}

fn prediction_from_aggs(
    home: &str,
    away: &str,
    teams: &HashMap<String, TeamAgg>,
    global_avg: f64,
    training_matches: usize,
    note: &str,
) -> SimplePrediction {
    let home_agg = teams.get(&canonical(home)).cloned().unwrap_or_default();
    let away_agg = teams.get(&canonical(away)).cloned().unwrap_or_default();

    let home_gf = if home_agg.matches > 0 { home_agg.goals_for / home_agg.matches as f64 } else { global_avg };
    let home_ga = if home_agg.matches > 0 { home_agg.goals_against / home_agg.matches as f64 } else { global_avg };
    let away_gf = if away_agg.matches > 0 { away_agg.goals_for / away_agg.matches as f64 } else { global_avg };
    let away_ga = if away_agg.matches > 0 { away_agg.goals_against / away_agg.matches as f64 } else { global_avg };

    let lambda_home = ((home_gf + away_ga) / 2.0).max(0.10);
    let lambda_away = ((away_gf + home_ga) / 2.0).max(0.10);

    let mat = score_matrix(lambda_home, lambda_away, 8);
    let mut p_home = 0.0;
    let mut p_draw = 0.0;
    let mut p_away = 0.0;
    let mut p_over25 = 0.0;
    let mut p_btts = 0.0;
    let mut best = (0u32, 0u32, 0.0f64);

    for i in 0..mat.len() {
        for j in 0..mat.len() {
            let p = mat[i][j];
            if i > j {
                p_home += p;
            } else if i == j {
                p_draw += p;
            } else {
                p_away += p;
            }
            if i + j >= 3 {
                p_over25 += p;
            }
            if i > 0 && j > 0 {
                p_btts += p;
            }
            if p > best.2 {
                best = (i as u32, j as u32, p);
            }
        }
    }

    SimplePrediction {
        home_team: home.to_string(),
        away_team: away.to_string(),
        lambda_home,
        lambda_away,
        outcome: OutcomeProbabilities {
            home: p_home,
            draw: p_draw,
            away: p_away,
        },
        over_25: p_over25,
        btts: p_btts,
        most_likely_score: (best.0, best.1),
        fair_odds_home: fair_odds(p_home),
        fair_odds_draw: fair_odds(p_draw),
        fair_odds_away: fair_odds(p_away),
        training_matches,
        note: note.to_string(),
    }
}

fn update_aggs(m: &MatchNormRow, teams: &mut HashMap<String, TeamAgg>, totals: &mut (f64, f64)) {
    let (Some(hg), Some(ag)) = (m.home_score, m.away_score) else {
        return;
    };
    let hkey = canonical(&m.home_team_name);
    let akey = canonical(&m.away_team_name);

    {
        let e = teams.entry(hkey).or_default();
        e.matches += 1;
        e.goals_for += hg as f64;
        e.goals_against += ag as f64;
    }
    {
        let e = teams.entry(akey).or_default();
        e.matches += 1;
        e.goals_for += ag as f64;
        e.goals_against += hg as f64;
    }
    totals.0 += (hg + ag) as f64;
    totals.1 += 2.0;
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

pub fn predict_from_pack(pack_dir: &Path, home: &str, away: &str) -> Result<SimplePrediction, String> {
    let matches = read_matches(pack_dir, 2_000_000)?;
    let mut teams: HashMap<String, TeamAgg> = HashMap::new();
    let mut totals = (0.0f64, 0.0f64);

    for m in &matches {
        if m.sport == "football" {
            update_aggs(m, &mut teams, &mut totals);
        }
    }

    let global_avg = if totals.1 > 0.0 { (totals.0 / totals.1).max(0.5) } else { 1.25 };
    Ok(prediction_from_aggs(
        home,
        away,
        &teams,
        global_avg,
        matches.len(),
        "v9 Rust simple aggregate Poisson over compressed pack. This is runtime proof, not final smart model.",
    ))
}

pub fn backtest_from_pack(pack_dir: &Path, min_train: usize, include_rows: bool) -> Result<BacktestSummary, String> {
    let matches = read_matches(pack_dir, 2_000_000)?;
    let mut football: Vec<MatchNormRow> = matches
        .into_iter()
        .filter(|m| m.sport == "football" && m.home_score.is_some() && m.away_score.is_some())
        .collect();

    football.sort_by(|a, b| {
        let da = a.match_date.clone().unwrap_or_default();
        let db = b.match_date.clone().unwrap_or_default();
        da.cmp(&db).then(a.match_id.cmp(&b.match_id))
    });

    let mut teams: HashMap<String, TeamAgg> = HashMap::new();
    let mut totals = (0.0f64, 0.0f64);
    let mut tested = Vec::new();

    for (idx, m) in football.iter().enumerate() {
        if idx >= min_train {
            let global_avg = if totals.1 > 0.0 { (totals.0 / totals.1).max(0.5) } else { 1.25 };
            let pred = prediction_from_aggs(
                &m.home_team_name,
                &m.away_team_name,
                &teams,
                global_avg,
                idx,
                "walk-forward",
            );

            let hg = m.home_score.unwrap();
            let ag = m.away_score.unwrap();
            let actual = actual_outcome(hg, ag);
            let pick = pick_from_probs(&pred.outcome);
            let actual_over25 = hg + ag >= 3;
            let actual_btts = hg > 0 && ag > 0;
            tested.push(BacktestRow {
                match_id: m.match_id.clone(),
                match_date: m.match_date.clone(),
                home_team: m.home_team_name.clone(),
                away_team: m.away_team_name.clone(),
                actual_home_goals: hg,
                actual_away_goals: ag,
                actual_outcome: actual.clone(),
                predicted_pick: pick,
                home_prob: pred.outcome.home,
                draw_prob: pred.outcome.draw,
                away_prob: pred.outcome.away,
                over_25_prob: pred.over_25,
                actual_over_25: actual_over25,
                btts_prob: pred.btts,
                actual_btts,
                log_loss: log_loss(&pred.outcome, &actual),
                brier: brier(&pred.outcome, &actual),
            });
        }
        update_aggs(m, &mut teams, &mut totals);
    }

    let n = tested.len().max(1) as f64;
    let acc = tested.iter().filter(|r| r.predicted_pick == r.actual_outcome).count() as f64 / n;
    let over_acc = tested.iter().filter(|r| (r.over_25_prob >= 0.5) == r.actual_over_25).count() as f64 / n;
    let btts_acc = tested.iter().filter(|r| (r.btts_prob >= 0.5) == r.actual_btts).count() as f64 / n;
    let ll = tested.iter().map(|r| r.log_loss).sum::<f64>() / n;
    let br = tested.iter().map(|r| r.brier).sum::<f64>() / n;

    let rows = if include_rows { tested } else { Vec::new() };

    Ok(BacktestSummary {
        ok: true,
        matches_total: football.len(),
        matches_tested: n as usize,
        min_train,
        one_x_two_accuracy: acc,
        over_25_accuracy: over_acc,
        btts_accuracy: btts_acc,
        log_loss: ll,
        brier: br,
        rows,
        note: "v9 Rust walk-forward baseline. It updates history after each match, so tested rows do not train on themselves.".to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn poisson_is_normalized_after_truncation() {
        let mat = score_matrix(1.4, 1.1, 8);
        let s: f64 = mat.iter().flat_map(|r| r.iter()).sum();
        assert!((s - 1.0).abs() < 1e-9);
    }
}
