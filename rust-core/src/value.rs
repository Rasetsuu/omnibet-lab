use crate::inference::{predict_from_pack, SimplePrediction};
use crate::odds::{expected_value, fair_odds, quarter_kelly};
use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct MarketPrice {
    pub market_id: String,
    pub selection: String,
    pub odds: f64,
    pub bookmaker: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ValueSelection {
    pub market_id: String,
    pub selection: String,
    pub bookmaker: String,
    pub model_probability: f64,
    pub fair_odds: f64,
    pub bookmaker_odds: f64,
    pub edge: f64,
    pub quarter_kelly: f64,
    pub decision: String,
    pub model_trust: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BetBuilderTicket {
    pub name: String,
    pub legs: Vec<ValueSelection>,
    pub combined_probability_independent: f64,
    pub combined_bookmaker_odds: f64,
    pub fair_odds_independent: f64,
    pub edge_independent: f64,
    pub correlation_risk: f64,
    pub adjusted_probability: f64,
    pub fair_odds_adjusted: f64,
    pub edge_adjusted: f64,
    pub quarter_kelly_adjusted: f64,
    pub decision: String,
    pub note: String,
    pub model_trust: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct ValueReport {
    pub ok: bool,
    pub home_team: String,
    pub away_team: String,
    pub selections: Vec<ValueSelection>,
    pub tickets: Vec<BetBuilderTicket>,
    pub note: String,
}

fn split_csv_line(line: &str) -> Vec<String> {
    // Minimal CSV parser enough for the current simple odds sample.
    // Future v13 can switch to the csv crate.
    line.split(',').map(|x| x.trim().trim_matches('"').to_string()).collect()
}

pub fn read_odds_csv(path: &Path) -> Result<Vec<MarketPrice>, String> {
    let text = fs::read_to_string(path)
        .map_err(|e| format!("failed to read odds CSV {}: {}", path.display(), e))?;
    let mut rows = Vec::new();
    for (idx, line) in text.lines().enumerate() {
        if idx == 0 || line.trim().is_empty() {
            continue;
        }
        let parts = split_csv_line(line);
        if parts.len() < 4 {
            continue;
        }
        let odds = parts[2]
            .parse::<f64>()
            .map_err(|e| format!("bad odds on line {}: {}", idx + 1, e))?;
        rows.push(MarketPrice {
            market_id: parts[0].clone(),
            selection: parts[1].clone(),
            odds,
            bookmaker: parts[3].clone(),
        });
    }
    Ok(rows)
}

pub fn probability_for_market(pred: &SimplePrediction, market_id: &str, selection: &str) -> Option<f64> {
    match (market_id, selection) {
        ("football.1x2", "home") => Some(pred.outcome.home),
        ("football.1x2", "draw") => Some(pred.outcome.draw),
        ("football.1x2", "away") => Some(pred.outcome.away),

        ("football.double_chance", "1X") => Some((pred.outcome.home + pred.outcome.draw).clamp(0.0, 1.0)),
        ("football.double_chance", "12") => Some((pred.outcome.home + pred.outcome.away).clamp(0.0, 1.0)),
        ("football.double_chance", "X2") => Some((pred.outcome.draw + pred.outcome.away).clamp(0.0, 1.0)),

        ("football.total_goals", "over_2.5") => Some(pred.over_25),
        ("football.total_goals", "under_2.5") => Some((1.0 - pred.over_25).clamp(0.0, 1.0)),

        ("football.btts", "yes") => Some(pred.btts),
        ("football.btts", "no") => Some((1.0 - pred.btts).clamp(0.0, 1.0)),

        // Conservative approximations until score distribution exposes more markets.
        ("football.total_goals", "over_1.5") => Some((pred.over_25 + 0.20).clamp(0.0, 0.98)),
        ("football.total_goals", "under_3.5") => Some((1.0 - pred.over_25 + 0.18).clamp(0.0, 0.98)),
        ("football.team_goals", "home_over_0.5") => Some((1.0 - (-pred.lambda_home).exp()).clamp(0.0, 1.0)),
        ("football.team_goals", "home_over_1.5") => {
            let p0 = (-pred.lambda_home).exp();
            let p1 = p0 * pred.lambda_home;
            Some((1.0 - p0 - p1).clamp(0.0, 1.0))
        }

        _ => None,
    }
}

fn decision(edge: f64, kelly: f64, model_trust: f64) -> String {
    if model_trust < 0.50 {
        return "PAPER ONLY - model trust too low".to_string();
    }
    if edge < 0.02 {
        "NO BET - edge too small".to_string()
    } else if kelly <= 0.0 {
        "NO BET - Kelly zero".to_string()
    } else if model_trust < 0.75 {
        "WATCHLIST VALUE - model not trusted enough for staking".to_string()
    } else if edge >= 0.08 {
        "STRONG VALUE - still verify market/liquidity".to_string()
    } else {
        "VALUE - small stake only".to_string()
    }
}

pub fn value_selections(pred: &SimplePrediction, prices: &[MarketPrice], model_trust: f64) -> Vec<ValueSelection> {
    let mut out = Vec::new();
    for price in prices {
        let Some(p) = probability_for_market(pred, &price.market_id, &price.selection) else {
            continue;
        };
        let ev = expected_value(p, price.odds).unwrap_or(-1.0);
        let qk = quarter_kelly(p, price.odds).unwrap_or(0.0);
        out.push(ValueSelection {
            market_id: price.market_id.clone(),
            selection: price.selection.clone(),
            bookmaker: price.bookmaker.clone(),
            model_probability: p,
            fair_odds: fair_odds(p),
            bookmaker_odds: price.odds,
            edge: ev,
            quarter_kelly: qk,
            decision: decision(ev, qk, model_trust),
            model_trust,
        });
    }
    out.sort_by(|a, b| b.edge.partial_cmp(&a.edge).unwrap_or(std::cmp::Ordering::Equal));
    out
}

fn find_sel<'a>(xs: &'a [ValueSelection], market: &str, selection: &str) -> Option<&'a ValueSelection> {
    xs.iter().find(|x| x.market_id == market && x.selection == selection)
}

fn ticket_decision(edge: f64, qk: f64, corr: f64, model_trust: f64) -> String {
    if model_trust < 0.50 {
        return "PAPER ONLY - model trust too low".to_string();
    }
    if corr >= 0.45 {
        "NO BET - correlation risk too high".to_string()
    } else if edge < 0.03 {
        "NO BET - combined edge too small".to_string()
    } else if qk <= 0.0 {
        "NO BET - Kelly zero".to_string()
    } else if edge >= 0.10 {
        "VALUE BUILDER - verify same-game pricing".to_string()
    } else {
        "SMALL VALUE BUILDER - tiny stake only".to_string()
    }
}

fn build_ticket(name: &str, legs: Vec<ValueSelection>, correlation_risk: f64, model_trust: f64) -> Option<BetBuilderTicket> {
    if legs.is_empty() {
        return None;
    }
    let mut p = 1.0;
    let mut odds = 1.0;
    for leg in &legs {
        p *= leg.model_probability;
        odds *= leg.bookmaker_odds;
    }
    let adjusted = (p * (1.0 - correlation_risk)).clamp(0.000001, 0.999999);
    let fair_ind = fair_odds(p);
    let fair_adj = fair_odds(adjusted);
    let edge_ind = p * odds - 1.0;
    let edge_adj = adjusted * odds - 1.0;
    let qk = quarter_kelly(adjusted, odds).unwrap_or(0.0);

    Some(BetBuilderTicket {
        name: name.to_string(),
        legs,
        combined_probability_independent: p,
        combined_bookmaker_odds: odds,
        fair_odds_independent: fair_ind,
        edge_independent: edge_ind,
        correlation_risk,
        adjusted_probability: adjusted,
        fair_odds_adjusted: fair_adj,
        edge_adjusted: edge_adj,
        quarter_kelly_adjusted: qk,
        decision: ticket_decision(edge_adj, qk, correlation_risk, model_trust),
        note: "v13 heuristic builder. Same-game correlation is approximated, not bookmaker-grade.".to_string(),
        model_trust,
    })
}

pub fn build_tickets(selections: &[ValueSelection], model_trust: f64) -> Vec<BetBuilderTicket> {
    let mut out = Vec::new();

    // Safe: low correlation, broad markets.
    if let (Some(dc), Some(u35)) = (
        find_sel(selections, "football.double_chance", "1X"),
        find_sel(selections, "football.total_goals", "under_3.5"),
    ) {
        if let Some(t) = build_ticket("Safe Builder", vec![dc.clone(), u35.clone()], 0.08, model_trust) {
            out.push(t);
        }
    }

    // Balanced: favorite result + goals.
    if let (Some(home), Some(over25)) = (
        find_sel(selections, "football.1x2", "home"),
        find_sel(selections, "football.total_goals", "over_2.5"),
    ) {
        if let Some(t) = build_ticket("Balanced Builder", vec![home.clone(), over25.clone()], 0.22, model_trust) {
            out.push(t);
        }
    }

    // Aggressive: result + goals + BTTS.
    if let (Some(home), Some(over25), Some(btts)) = (
        find_sel(selections, "football.1x2", "home"),
        find_sel(selections, "football.total_goals", "over_2.5"),
        find_sel(selections, "football.btts", "yes"),
    ) {
        if let Some(t) = build_ticket("Aggressive Builder", vec![home.clone(), over25.clone(), btts.clone()], 0.38, model_trust) {
            out.push(t);
        }
    }

    out.sort_by(|a, b| b.edge_adjusted.partial_cmp(&a.edge_adjusted).unwrap_or(std::cmp::Ordering::Equal));
    out
}

pub fn value_report_from_pack(
    pack_dir: &Path,
    home: &str,
    away: &str,
    odds_csv: &Path,
    model_trust: f64,
) -> Result<ValueReport, String> {
    let pred = predict_from_pack(pack_dir, home, away)?;
    let prices = read_odds_csv(odds_csv)?;
    let trust = model_trust.clamp(0.0, 1.0);
    let selections = value_selections(&pred, &prices, trust);
    let tickets = build_tickets(&selections, trust);

    Ok(ValueReport {
        ok: true,
        home_team: home.to_string(),
        away_team: away.to_string(),
        selections,
        tickets,
        note: format!("v13 Rust value runtime. model_trust={:.2}. Uses simple prediction model; do not treat as betting advice.", trust),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decision_rejects_negative_edge() {
        assert!(decision(-0.1, 0.0, 0.80).starts_with("NO BET"));
    }

    #[test]
    fn low_trust_blocks_staking_labels() {
        assert!(decision(0.50, 0.10, 0.25).starts_with("PAPER ONLY"));
    }

    #[test]
    fn csv_parser_simple() {
        let parts = split_csv_line("football.1x2,home,1.62,Book");
        assert_eq!(parts.len(), 4);
        assert_eq!(parts[1], "home");
    }
}
