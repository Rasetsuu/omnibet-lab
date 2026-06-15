use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub match_id: String,
    pub sport: String,
    pub match_date: String,
    pub competition_id: Option<String>,
    pub season_id: Option<String>,
    pub home_team_id: Option<String>,
    pub away_team_id: Option<String>,
    pub home_team_name: String,
    pub away_team_name: String,
    pub home_score: Option<i32>,
    pub away_score: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    pub team_id: String,
    pub sport: String,
    pub name: String,
    pub country: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub player_id: String,
    pub sport: String,
    pub name: String,
    pub nationality: Option<String>,
    pub position: Option<String>,
    pub current_team_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchEvent {
    pub event_id: String,
    pub match_id: String,
    pub event_type: String,
    pub minute: Option<i32>,
    pub second: Option<i32>,
    pub team_id: Option<String>,
    pub player_id: Option<String>,
    pub xg: Option<f64>,
    pub outcome: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OddsSnapshot {
    pub odds_id: String,
    pub match_id: String,
    pub bookmaker: Option<String>,
    pub market_id: String,
    pub selection: String,
    pub line: Option<f64>,
    pub odds_decimal: f64,
    pub captured_at: String,
    pub is_live: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Prediction {
    pub market_id: String,
    pub selection: String,
    pub probability: f64,
    pub fair_odds: f64,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketDefinition {
    pub market_id: String,
    pub sport: String,
    pub family: String,
    pub requires_team: bool,
    pub requires_player: bool,
    pub requires_line: bool,
    pub requires_minute: bool,
    pub correlation_tags: Vec<String>,
}
