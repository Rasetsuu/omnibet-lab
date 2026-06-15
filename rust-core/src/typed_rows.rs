use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::pack::table_rows_as_json;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchNormRow {
    pub match_id: String,
    pub source_id: Option<String>,
    pub sport: String,
    pub competition_id: Option<String>,
    pub season_id: Option<String>,
    pub match_date: Option<String>,
    pub status: Option<String>,
    pub home_team_id: Option<String>,
    pub away_team_id: Option<String>,
    pub home_team_name: String,
    pub away_team_name: String,
    pub home_score: Option<i32>,
    pub away_score: Option<i32>,
    pub venue: Option<String>,
    pub raw_json: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoldMatchFeatureRow {
    pub feature_id: String,
    pub match_id: String,
    pub source_id: Option<String>,
    pub sport: String,
    pub match_date: Option<String>,
    pub competition_id: Option<String>,
    pub season_id: Option<String>,
    pub home_team_id: Option<String>,
    pub away_team_id: Option<String>,
    pub home_team_name: String,
    pub away_team_name: String,
    pub target_home_goals: Option<i32>,
    pub target_away_goals: Option<i32>,
    pub target_outcome: Option<String>,
    pub target_over_25: Option<i32>,
    pub target_btts: Option<i32>,
    pub feature_version: String,
    pub features_json: String,
    pub created_at: Option<String>,
}

pub fn read_matches(pack_dir: &Path, limit: usize) -> Result<Vec<MatchNormRow>, String> {
    let rows = table_rows_as_json(pack_dir, "matches_norm", limit)?;
    rows.into_iter()
        .map(|v| serde_json::from_value::<MatchNormRow>(v).map_err(|e| e.to_string()))
        .collect()
}

pub fn read_gold_match_features(pack_dir: &Path, limit: usize) -> Result<Vec<GoldMatchFeatureRow>, String> {
    let rows = table_rows_as_json(pack_dir, "gold_match_features", limit)?;
    rows.into_iter()
        .map(|v| serde_json::from_value::<GoldMatchFeatureRow>(v).map_err(|e| e.to_string()))
        .collect()
}

pub fn parse_feature_json(row: &GoldMatchFeatureRow) -> Result<Value, String> {
    serde_json::from_str(&row.features_json).map_err(|e| e.to_string())
}
