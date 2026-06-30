use crate::adapter_normalizer_v621::{
    build_normalized_historical_pack_v621, normalize_sample_event_v621,
    normalize_sample_fixture_v621, normalize_sample_result_v621, validate_normalized_pack_v621,
    NormalizedEventRowV621, NormalizedFixtureRowV621, NormalizedHistoricalPackV621,
    NormalizedResultRowV621,
};
use serde::Deserialize;

fn slug_v651(value: &str) -> String {
    value
        .trim()
        .to_lowercase()
        .replace(' ', "-")
        .replace('/', "-")
}

fn parse_u16_v651(value: &str, field: &str) -> Result<u16, String> {
    value
        .trim()
        .parse::<u16>()
        .map_err(|err| format!("failed to parse {field} as u16: {err}"))
}

fn csv_index_v651(headers: &[&str], name: &str) -> Result<usize, String> {
    headers
        .iter()
        .position(|header| *header == name)
        .ok_or_else(|| format!("missing csv header: {name}"))
}

pub fn parse_football_data_csv_v651(
    content: &str,
) -> Result<(Vec<NormalizedFixtureRowV621>, Vec<NormalizedResultRowV621>), String> {
    let mut lines = content.lines().filter(|line| !line.trim().is_empty());
    let header_line = lines.next().ok_or_else(|| "csv content is empty".to_owned())?;
    let headers: Vec<&str> = header_line.split(',').map(str::trim).collect();
    let date_idx = csv_index_v651(&headers, "Date")?;
    let home_idx = csv_index_v651(&headers, "HomeTeam")?;
    let away_idx = csv_index_v651(&headers, "AwayTeam")?;
    let home_score_idx = csv_index_v651(&headers, "FTHG")?;
    let away_score_idx = csv_index_v651(&headers, "FTAG")?;

    let mut fixtures = Vec::new();
    let mut results = Vec::new();
    for line in lines {
        let cols: Vec<&str> = line.split(',').map(str::trim).collect();
        if cols.len() < headers.len() {
            return Err(format!("csv row has too few columns: {line}"));
        }
        let date = cols[date_idx];
        let home = cols[home_idx];
        let away = cols[away_idx];
        let home_score = parse_u16_v651(cols[home_score_idx], "FTHG")?;
        let away_score = parse_u16_v651(cols[away_score_idx], "FTAG")?;
        let fixture_id = format!("csv-{}-{}-{}", slug_v651(home), slug_v651(away), date);
        let kickoff_utc = format!("{date}T00:00:00Z");
        fixtures.push(normalize_sample_fixture_v621(
            "csv_match_sample",
            &fixture_id,
            &kickoff_utc,
            home,
            away,
        ));
        results.push(normalize_sample_result_v621(
            "csv_match_sample",
            &fixture_id,
            home_score,
            away_score,
            &format!("{date}T23:59:00Z"),
        ));
    }
    Ok((fixtures, results))
}

#[derive(Debug, Deserialize)]
struct OpenFootballSampleV651 {
    matches: Vec<OpenFootballMatchV651>,
}

#[derive(Debug, Deserialize)]
struct OpenFootballMatchV651 {
    date: String,
    round: Option<String>,
    team1: String,
    team2: String,
    score: OpenFootballScoreV651,
}

#[derive(Debug, Deserialize)]
struct OpenFootballScoreV651 {
    ft: [u16; 2],
}

pub fn parse_openfootball_json_v651(
    content: &str,
) -> Result<(Vec<NormalizedFixtureRowV621>, Vec<NormalizedResultRowV621>), String> {
    let payload: OpenFootballSampleV651 =
        serde_json::from_str(content).map_err(|err| format!("failed to parse json match sample: {err}"))?;
    let mut fixtures = Vec::new();
    let mut results = Vec::new();
    for row in payload.matches {
        let fixture_id = format!("json-{}-{}-{}", slug_v651(&row.team1), slug_v651(&row.team2), row.date);
        let kickoff_utc = format!("{}T00:00:00Z", row.date);
        let _round = row.round;
        fixtures.push(normalize_sample_fixture_v621(
            "json_match_sample",
            &fixture_id,
            &kickoff_utc,
            &row.team1,
            &row.team2,
        ));
        results.push(normalize_sample_result_v621(
            "json_match_sample",
            &fixture_id,
            row.score.ft[0],
            row.score.ft[1],
            &format!("{}T23:59:00Z", row.date),
        ));
    }
    Ok((fixtures, results))
}

#[derive(Debug, Deserialize)]
struct EventSampleV651 {
    events: Vec<EventRowV651>,
}

#[derive(Debug, Deserialize)]
struct EventRowV651 {
    fixture_id: String,
    minute: u16,
    team: String,
    #[serde(rename = "type")]
    event_type: EventNameV651,
    player: Option<EventNameV651>,
}

#[derive(Debug, Deserialize)]
struct EventNameV651 {
    name: String,
}

pub fn parse_statsbomb_events_json_v651(
    content: &str,
) -> Result<Vec<NormalizedEventRowV621>, String> {
    let payload: EventSampleV651 =
        serde_json::from_str(content).map_err(|err| format!("failed to parse json event sample: {err}"))?;
    Ok(payload
        .events
        .into_iter()
        .map(|event| {
            normalize_sample_event_v621(
                "json_event_sample",
                &event.fixture_id,
                &event.event_type.name,
                &event.team,
                event.minute,
                event.player.as_ref().map(|player| player.name.as_str()),
            )
        })
        .collect())
}

pub fn build_pack_from_sample_contents_v651(
    csv_content: &str,
    json_match_content: &str,
    event_content: &str,
) -> Result<NormalizedHistoricalPackV621, String> {
    let (mut csv_fixtures, mut csv_results) = parse_football_data_csv_v651(csv_content)?;
    let (json_fixtures, json_results) = parse_openfootball_json_v651(json_match_content)?;
    let events = parse_statsbomb_events_json_v651(event_content)?;
    csv_fixtures.extend(json_fixtures);
    csv_results.extend(json_results);
    let pack = build_normalized_historical_pack_v621(csv_fixtures, csv_results, events);
    validate_normalized_pack_v621(&pack)?;
    Ok(pack)
}

#[cfg(test)]
mod tests {
    use super::*;

    const CSV_SAMPLE: &str = "Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n2026-06-29,Brazil,Japan,2,1,H\n2026-06-29,Germany,Paraguay,1,1,D\n";
    const JSON_MATCH_SAMPLE: &str = r#"{"matches":[{"date":"2026-06-29","round":"Round of 32","team1":"Brazil","team2":"Japan","score":{"ft":[2,1]}}]}"#;
    const EVENT_SAMPLE: &str = r#"{"events":[{"fixture_id":"sample-brazil-japan-20260629","minute":12,"team":"Brazil","type":{"name":"Shot"},"player":{"name":"Brazil Player A"}}]}"#;

    #[test]
    fn parses_csv_sample_v651() {
        let (fixtures, results) = parse_football_data_csv_v651(CSV_SAMPLE).unwrap();
        assert_eq!(fixtures.len(), 2);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].result_label, "home_win");
        assert_eq!(results[1].result_label, "draw");
    }

    #[test]
    fn builds_pack_from_sample_contents_v651() {
        let pack = build_pack_from_sample_contents_v651(CSV_SAMPLE, JSON_MATCH_SAMPLE, EVENT_SAMPLE).unwrap();
        assert_eq!(pack.fixtures.len(), 3);
        assert_eq!(pack.results.len(), 3);
        assert_eq!(pack.events.len(), 1);
        assert!(!pack.ready_for_real_model);
    }
}
