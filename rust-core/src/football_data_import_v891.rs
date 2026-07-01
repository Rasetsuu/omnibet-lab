use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FootballDataImportConfigV891 {
    pub source_id: String,
    pub competition_id: String,
    pub season_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FootballDataMatchRowV891 {
    pub schema: String,
    pub source_id: String,
    pub competition_id: String,
    pub season_id: String,
    pub source_match_id: String,
    pub match_date: String,
    pub kickoff_time: Option<String>,
    pub home_team_raw: String,
    pub away_team_raw: String,
    pub final_home_goals: i64,
    pub final_away_goals: i64,
    pub full_time_result: String,
    pub half_time_home_goals: Option<i64>,
    pub half_time_away_goals: Option<i64>,
    pub half_time_result: Option<String>,
    pub status: String,
    pub payload_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FootballDataOddsRowV891 {
    pub schema: String,
    pub source_id: String,
    pub competition_id: String,
    pub season_id: String,
    pub source_match_id: String,
    pub market_family: String,
    pub market_scope: String,
    pub bookmaker: String,
    pub selection_key: String,
    pub price_decimal: f64,
    pub snapshot_kind: String,
    pub source_column: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FootballDataSkippedRowV891 {
    pub row_number: usize,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FootballDataImportReportV891 {
    pub schema: String,
    pub source_id: String,
    pub competition_id: String,
    pub season_id: String,
    pub input_rows: usize,
    pub match_rows: usize,
    pub odds_rows: usize,
    pub skipped_rows: Vec<FootballDataSkippedRowV891>,
    pub duplicate_match_ids: Vec<String>,
    pub missing_required_rows: usize,
    pub invalid_score_rows: usize,
    pub invalid_odds_rows: usize,
    pub bookmaker_count: usize,
    pub market_families: Vec<String>,
    pub ready_for_feature_build: bool,
    pub ready_for_training: bool,
    pub status: String,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FootballDataImportOutputV891 {
    pub matches: Vec<FootballDataMatchRowV891>,
    pub odds: Vec<FootballDataOddsRowV891>,
    pub report: FootballDataImportReportV891,
}

#[derive(Debug, Clone)]
struct ParsedCsvV891 {
    headers: Vec<String>,
    rows: Vec<Vec<String>>,
}

pub fn parse_football_data_csv_v891(
    text: &str,
    config: &FootballDataImportConfigV891,
) -> Result<FootballDataImportOutputV891, String> {
    let csv = parse_csv_v891(text)?;
    let header_index = build_header_index_v891(&csv.headers);
    for required in ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"] {
        if !header_index.contains_key(&normalize_header_v891(required)) {
            return Err(format!("missing required Football-Data column: {required}"));
        }
    }

    let mut matches = Vec::new();
    let mut odds = Vec::new();
    let mut skipped_rows = Vec::new();
    let mut duplicate_match_ids = Vec::new();
    let mut seen_match_ids = BTreeSet::new();
    let mut invalid_score_rows = 0;
    let mut invalid_odds_rows = 0;

    for (idx, raw_row) in csv.rows.iter().enumerate() {
        let row_number = idx + 2;
        let home = get_cell_v891(raw_row, &header_index, "HomeTeam").unwrap_or_default();
        let away = get_cell_v891(raw_row, &header_index, "AwayTeam").unwrap_or_default();
        let date_raw = get_cell_v891(raw_row, &header_index, "Date").unwrap_or_default();
        if home.trim().is_empty() || away.trim().is_empty() || date_raw.trim().is_empty() {
            skipped_rows.push(FootballDataSkippedRowV891 {
                row_number,
                reason: "missing_required_match_identity".to_string(),
            });
            continue;
        }

        let match_date = match normalize_date_v891(&date_raw) {
            Some(value) => value,
            None => {
                skipped_rows.push(FootballDataSkippedRowV891 {
                    row_number,
                    reason: format!("invalid_date:{date_raw}"),
                });
                continue;
            }
        };
        let final_home_goals = match parse_i64_cell_v891(raw_row, &header_index, "FTHG") {
            Some(value) => value,
            None => {
                invalid_score_rows += 1;
                skipped_rows.push(FootballDataSkippedRowV891 {
                    row_number,
                    reason: "invalid_or_missing_fthg".to_string(),
                });
                continue;
            }
        };
        let final_away_goals = match parse_i64_cell_v891(raw_row, &header_index, "FTAG") {
            Some(value) => value,
            None => {
                invalid_score_rows += 1;
                skipped_rows.push(FootballDataSkippedRowV891 {
                    row_number,
                    reason: "invalid_or_missing_ftag".to_string(),
                });
                continue;
            }
        };

        let computed_result = result_key_v891(final_home_goals, final_away_goals);
        let full_time_result = get_cell_v891(raw_row, &header_index, "FTR")
            .filter(|value| matches!(value.as_str(), "H" | "D" | "A"))
            .unwrap_or(computed_result);
        let half_time_home_goals = parse_i64_cell_v891(raw_row, &header_index, "HTHG");
        let half_time_away_goals = parse_i64_cell_v891(raw_row, &header_index, "HTAG");
        let half_time_result = match (half_time_home_goals, half_time_away_goals) {
            (Some(h), Some(a)) => Some(result_key_v891(h, a)),
            _ => get_cell_v891(raw_row, &header_index, "HTR").filter(|value| matches!(value.as_str(), "H" | "D" | "A")),
        };
        let kickoff_time = get_cell_v891(raw_row, &header_index, "Time").filter(|value| !value.trim().is_empty());
        let source_match_id = source_match_id_v891(config, &match_date, &home, &away);
        if !seen_match_ids.insert(source_match_id.clone()) {
            duplicate_match_ids.push(source_match_id.clone());
            skipped_rows.push(FootballDataSkippedRowV891 {
                row_number,
                reason: format!("duplicate_match_id:{source_match_id}"),
            });
            continue;
        }
        let payload_sha256 = row_payload_sha256_v891(raw_row);
        matches.push(FootballDataMatchRowV891 {
            schema: "omnibet.football_data_match_row.v891".to_string(),
            source_id: config.source_id.clone(),
            competition_id: config.competition_id.clone(),
            season_id: config.season_id.clone(),
            source_match_id: source_match_id.clone(),
            match_date,
            kickoff_time,
            home_team_raw: home,
            away_team_raw: away,
            final_home_goals,
            final_away_goals,
            full_time_result,
            half_time_home_goals,
            half_time_away_goals,
            half_time_result,
            status: "final".to_string(),
            payload_sha256,
        });
        let before = odds.len();
        extract_odds_rows_v891(raw_row, &header_index, config, &source_match_id, &mut odds, &mut invalid_odds_rows);
        if odds.len() == before {
            // Missing odds is not fatal: results-only packs can still support team-result features.
        }
    }

    let mut bookmakers = BTreeSet::new();
    let mut market_families = BTreeSet::new();
    for row in &odds {
        bookmakers.insert(row.bookmaker.clone());
        market_families.insert(row.market_family.clone());
    }
    let ready_for_feature_build = !matches.is_empty() && duplicate_match_ids.is_empty();
    let status = if ready_for_feature_build {
        "imported_for_feature_build"
    } else {
        "blocked_import"
    };
    let mut notes = vec![
        "Football-Data import is historical/offline only; no live provider calls are made.".to_string(),
        "ready_for_training remains false until a separate feature-count/evaluation gate passes.".to_string(),
    ];
    if odds.is_empty() {
        notes.push("No supported odds columns were found; this batch is results-only.".to_string());
    }
    let report = FootballDataImportReportV891 {
        schema: "omnibet.football_data_import_report.v891".to_string(),
        source_id: config.source_id.clone(),
        competition_id: config.competition_id.clone(),
        season_id: config.season_id.clone(),
        input_rows: csv.rows.len(),
        match_rows: matches.len(),
        odds_rows: odds.len(),
        skipped_rows,
        duplicate_match_ids,
        missing_required_rows: csv.rows.len().saturating_sub(matches.len()).saturating_sub(invalid_score_rows),
        invalid_score_rows,
        invalid_odds_rows,
        bookmaker_count: bookmakers.len(),
        market_families: market_families.into_iter().collect(),
        ready_for_feature_build,
        ready_for_training: false,
        status: status.to_string(),
        notes,
    };
    Ok(FootballDataImportOutputV891 { matches, odds, report })
}

pub fn write_football_data_import_outputs_v891(output: &FootballDataImportOutputV891, out_dir: &Path) -> Result<(), String> {
    fs::create_dir_all(out_dir).map_err(|e| format!("create {}: {e}", out_dir.display()))?;
    write_jsonl_v891(&out_dir.join("matches.jsonl"), &output.matches)?;
    write_jsonl_v891(&out_dir.join("odds.jsonl"), &output.odds)?;
    let report_text = serde_json::to_string_pretty(&output.report).map_err(|e| format!("serialize import report: {e}"))?;
    fs::write(out_dir.join("import_report.json"), format!("{report_text}\n"))
        .map_err(|e| format!("write import_report.json: {e}"))?;
    Ok(())
}

fn write_jsonl_v891<T: Serialize>(path: &Path, rows: &[T]) -> Result<(), String> {
    let mut out = String::new();
    for row in rows {
        out.push_str(&serde_json::to_string(row).map_err(|e| format!("serialize jsonl row: {e}"))?);
        out.push('\n');
    }
    fs::write(path, out).map_err(|e| format!("write {}: {e}", path.display()))
}

fn extract_odds_rows_v891(
    raw_row: &[String],
    header_index: &BTreeMap<String, usize>,
    config: &FootballDataImportConfigV891,
    source_match_id: &str,
    out: &mut Vec<FootballDataOddsRowV891>,
    invalid_odds_rows: &mut usize,
) {
    for spec in odds_specs_v891() {
        let Some(price_text) = get_cell_v891(raw_row, header_index, spec.column) else { continue; };
        if price_text.trim().is_empty() {
            continue;
        }
        match price_text.parse::<f64>() {
            Ok(price) if price.is_finite() && price > 1.0 => out.push(FootballDataOddsRowV891 {
                schema: "omnibet.football_data_odds_row.v891".to_string(),
                source_id: config.source_id.clone(),
                competition_id: config.competition_id.clone(),
                season_id: config.season_id.clone(),
                source_match_id: source_match_id.to_string(),
                market_family: spec.market_family.to_string(),
                market_scope: spec.market_scope.to_string(),
                bookmaker: spec.bookmaker.to_string(),
                selection_key: spec.selection_key.to_string(),
                price_decimal: price,
                snapshot_kind: spec.snapshot_kind.to_string(),
                source_column: spec.column.to_string(),
            }),
            _ => *invalid_odds_rows += 1,
        }
    }
}

#[derive(Debug, Clone, Copy)]
struct OddsSpecV891 {
    column: &'static str,
    market_family: &'static str,
    market_scope: &'static str,
    bookmaker: &'static str,
    selection_key: &'static str,
    snapshot_kind: &'static str,
}

fn odds_specs_v891() -> Vec<OddsSpecV891> {
    let mut specs = Vec::new();
    for (prefix, bookmaker, snapshot_kind) in [
        ("B365", "Bet365", "pre_match"),
        ("BW", "Bet&Win", "pre_match"),
        ("IW", "Interwetten", "pre_match"),
        ("PS", "Pinnacle_Sports", "pre_match"),
        ("WH", "William_Hill", "pre_match"),
        ("VC", "Victor_Chandler", "pre_match"),
        ("Max", "Market_Max", "aggregate_max"),
        ("Avg", "Market_Average", "aggregate_average"),
        ("B365C", "Bet365", "closing"),
        ("BWC", "Bet&Win", "closing"),
        ("IWC", "Interwetten", "closing"),
        ("PSC", "Pinnacle_Sports", "closing"),
        ("WHC", "William_Hill", "closing"),
        ("VCC", "Victor_Chandler", "closing"),
        ("MaxC", "Market_Max", "closing_aggregate_max"),
        ("AvgC", "Market_Average", "closing_aggregate_average"),
    ] {
        specs.push(OddsSpecV891 { column: Box::leak(format!("{prefix}H").into_boxed_str()), market_family: "1x2", market_scope: "regulation_90", bookmaker, selection_key: "home", snapshot_kind });
        specs.push(OddsSpecV891 { column: Box::leak(format!("{prefix}D").into_boxed_str()), market_family: "1x2", market_scope: "regulation_90", bookmaker, selection_key: "draw", snapshot_kind });
        specs.push(OddsSpecV891 { column: Box::leak(format!("{prefix}A").into_boxed_str()), market_family: "1x2", market_scope: "regulation_90", bookmaker, selection_key: "away", snapshot_kind });
    }
    for (over_col, under_col, bookmaker, snapshot_kind) in [
        ("B365>2.5", "B365<2.5", "Bet365", "pre_match"),
        ("P>2.5", "P<2.5", "Pinnacle_Sports", "pre_match"),
        ("Max>2.5", "Max<2.5", "Market_Max", "aggregate_max"),
        ("Avg>2.5", "Avg<2.5", "Market_Average", "aggregate_average"),
        ("B365C>2.5", "B365C<2.5", "Bet365", "closing"),
        ("PC>2.5", "PC<2.5", "Pinnacle_Sports", "closing"),
        ("MaxC>2.5", "MaxC<2.5", "Market_Max", "closing_aggregate_max"),
        ("AvgC>2.5", "AvgC<2.5", "Market_Average", "closing_aggregate_average"),
    ] {
        specs.push(OddsSpecV891 { column: over_col, market_family: "total_goals_2_5", market_scope: "regulation_90", bookmaker, selection_key: "over_2_5", snapshot_kind });
        specs.push(OddsSpecV891 { column: under_col, market_family: "total_goals_2_5", market_scope: "regulation_90", bookmaker, selection_key: "under_2_5", snapshot_kind });
    }
    specs
}

fn parse_csv_v891(text: &str) -> Result<ParsedCsvV891, String> {
    let mut rows = Vec::new();
    let mut row = Vec::new();
    let mut cell = String::new();
    let mut in_quotes = false;
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        match ch {
            '"' if in_quotes && chars.peek() == Some(&'"') => {
                cell.push('"');
                chars.next();
            }
            '"' => in_quotes = !in_quotes,
            ',' if !in_quotes => {
                row.push(cell.trim().to_string());
                cell.clear();
            }
            '\n' if !in_quotes => {
                row.push(cell.trim().trim_end_matches('\r').to_string());
                cell.clear();
                if row.iter().any(|value| !value.is_empty()) {
                    rows.push(row);
                }
                row = Vec::new();
            }
            _ => cell.push(ch),
        }
    }
    if !cell.is_empty() || !row.is_empty() {
        row.push(cell.trim().trim_end_matches('\r').to_string());
        if row.iter().any(|value| !value.is_empty()) {
            rows.push(row);
        }
    }
    if rows.is_empty() {
        return Err("CSV is empty".to_string());
    }
    let headers = rows.remove(0);
    Ok(ParsedCsvV891 { headers, rows })
}

fn build_header_index_v891(headers: &[String]) -> BTreeMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(idx, value)| (normalize_header_v891(value), idx))
        .collect()
}

fn normalize_header_v891(value: &str) -> String {
    value.trim().to_ascii_lowercase()
}

fn get_cell_v891(row: &[String], header_index: &BTreeMap<String, usize>, header: &str) -> Option<String> {
    let idx = *header_index.get(&normalize_header_v891(header))?;
    row.get(idx).map(|value| value.trim().to_string()).filter(|value| !value.is_empty())
}

fn parse_i64_cell_v891(row: &[String], header_index: &BTreeMap<String, usize>, header: &str) -> Option<i64> {
    get_cell_v891(row, header_index, header).and_then(|value| value.parse::<i64>().ok())
}

fn normalize_date_v891(value: &str) -> Option<String> {
    let value = value.trim();
    if value.len() == 10 && value.chars().nth(4) == Some('-') && value.chars().nth(7) == Some('-') {
        return Some(value.to_string());
    }
    let sep = if value.contains('/') { '/' } else if value.contains('-') { '-' } else { return None; };
    let parts: Vec<&str> = value.split(sep).collect();
    if parts.len() != 3 {
        return None;
    }
    let day = parts[0].parse::<u32>().ok()?;
    let month = parts[1].parse::<u32>().ok()?;
    let mut year = parts[2].parse::<u32>().ok()?;
    if year < 100 {
        year = if year >= 70 { 1900 + year } else { 2000 + year };
    }
    if !(1..=31).contains(&day) || !(1..=12).contains(&month) || year < 1900 {
        return None;
    }
    Some(format!("{year:04}-{month:02}-{day:02}"))
}

fn result_key_v891(home_goals: i64, away_goals: i64) -> String {
    if home_goals > away_goals {
        "H".to_string()
    } else if home_goals < away_goals {
        "A".to_string()
    } else {
        "D".to_string()
    }
}

fn source_match_id_v891(config: &FootballDataImportConfigV891, match_date: &str, home: &str, away: &str) -> String {
    format!(
        "football_data:{}:{}:{}:{}:{}",
        slug_v891(&config.competition_id),
        slug_v891(&config.season_id),
        match_date,
        slug_v891(home),
        slug_v891(away),
    )
}

fn slug_v891(value: &str) -> String {
    let mut out = String::new();
    let mut last_dash = false;
    for ch in value.trim().chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
            last_dash = false;
        } else if !last_dash {
            out.push('-');
            last_dash = true;
        }
    }
    out.trim_matches('-').to_string()
}

fn row_payload_sha256_v891(row: &[String]) -> String {
    let mut hasher = Sha256::new();
    for cell in row {
        hasher.update(cell.as_bytes());
        hasher.update(b"\x1f");
    }
    format!("{:x}", hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn config() -> FootballDataImportConfigV891 {
        FootballDataImportConfigV891 {
            source_id: "football_data_co_uk".to_string(),
            competition_id: "england_premier_league".to_string(),
            season_id: "2024_2025".to_string(),
        }
    }

    #[test]
    fn parses_football_data_csv_with_match_and_odds_rows() {
        let text = "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,B365H,B365D,B365A,B365>2.5,B365<2.5,B365CH,B365CD,B365CA\nE0,16/08/24,20:00,Man United,Fulham,1,0,H,0,0,D,1.65,4.10,5.25,1.80,2.00,1.60,4.20,5.50\nE0,17/08/24,12:30,Ipswich,Liverpool,0,2,A,0,0,D,8.00,5.20,1.36,1.65,2.20,8.50,5.40,1.33\n";
        let output = parse_football_data_csv_v891(text, &config()).expect("parse fixture csv");
        assert_eq!(output.matches.len(), 2);
        assert_eq!(output.report.input_rows, 2);
        assert_eq!(output.report.match_rows, 2);
        assert!(output.report.ready_for_feature_build);
        assert!(!output.report.ready_for_training);
        assert!(output.odds.iter().any(|row| row.market_family == "1x2" && row.selection_key == "home"));
        assert!(output.odds.iter().any(|row| row.market_family == "total_goals_2_5" && row.selection_key == "over_2_5"));
        assert!(output.odds.iter().any(|row| row.snapshot_kind == "closing"));
        assert_eq!(output.matches[0].match_date, "2024-08-16");
        assert_eq!(output.matches[0].full_time_result, "H");
    }

    #[test]
    fn skips_incomplete_or_duplicate_match_rows() {
        let text = "Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H\n16/08/24,Man United,Fulham,1,0,H,1.65\n16/08/24,Man United,Fulham,1,0,H,1.65\n17/08/24,Liverpool,,2,0,H,1.20\n18/08/24,Chelsea,Man City,x,2,A,4.00\n";
        let output = parse_football_data_csv_v891(text, &config()).expect("parse fixture csv");
        assert_eq!(output.matches.len(), 1);
        assert_eq!(output.report.duplicate_match_ids.len(), 1);
        assert_eq!(output.report.invalid_score_rows, 1);
        assert_eq!(output.report.skipped_rows.len(), 3);
        assert!(!output.report.ready_for_feature_build);
    }

    #[test]
    fn rejects_csv_missing_required_columns() {
        let err = parse_football_data_csv_v891("Date,HomeTeam,AwayTeam\n16/08/24,A,B\n", &config())
            .expect_err("missing score columns should fail");
        assert!(err.contains("missing required"));
    }
}
