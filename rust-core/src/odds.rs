pub fn fair_odds(probability: f64) -> f64 {
    let p = probability.clamp(0.000001, 0.999999);
    1.0 / p
}

pub fn implied_probability(decimal_odds: f64) -> Option<f64> {
    if decimal_odds > 1.0 {
        Some(1.0 / decimal_odds)
    } else {
        None
    }
}

pub fn expected_value(probability: f64, decimal_odds: f64) -> Option<f64> {
    if decimal_odds <= 1.0 {
        None
    } else {
        Some(probability * decimal_odds - 1.0)
    }
}

pub fn kelly_fraction(probability: f64, decimal_odds: f64) -> Option<f64> {
    if decimal_odds <= 1.0 {
        return None;
    }
    let p = probability.clamp(0.0, 1.0);
    let b = decimal_odds - 1.0;
    let q = 1.0 - p;
    let k = (b * p - q) / b;
    Some(k.clamp(0.0, 1.0))
}

pub fn quarter_kelly(probability: f64, decimal_odds: f64) -> Option<f64> {
    kelly_fraction(probability, decimal_odds).map(|k| k * 0.25)
}

pub fn remove_overround_multiplicative(odds: &[f64]) -> Option<Vec<f64>> {
    if odds.is_empty() || odds.iter().any(|&o| o <= 1.0) {
        return None;
    }
    let inv: Vec<f64> = odds.iter().map(|o| 1.0 / o).collect();
    let sum: f64 = inv.iter().sum();
    if sum <= 0.0 {
        return None;
    }
    Some(inv.iter().map(|p| p / sum).collect())
}

pub fn outcome_from_score(home: i32, away: i32) -> &'static str {
    if home > away {
        "H"
    } else if home < away {
        "A"
    } else {
        "D"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn odds_math_works() {
        assert!((fair_odds(0.5) - 2.0).abs() < 1e-9);
        assert!((implied_probability(2.0).unwrap() - 0.5).abs() < 1e-9);
        assert!(expected_value(0.55, 2.0).unwrap() > 0.0);
        assert!(quarter_kelly(0.55, 2.0).unwrap() > 0.0);
    }

    #[test]
    fn overround_removal_sums_to_one() {
        let p = remove_overround_multiplicative(&[2.7, 2.3, 4.4]).unwrap();
        let s: f64 = p.iter().sum();
        assert!((s - 1.0).abs() < 1e-9);
    }
}
