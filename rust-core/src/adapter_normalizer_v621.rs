#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedFixtureRowV621 {
    pub source_id: String,
    pub fixture_id: String,
    pub kickoff_utc: String,
    pub home_name: String,
    pub away_name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedResultRowV621 {
    pub source_id: String,
    pub fixture_id: String,
    pub home_score: u16,
    pub away_score: u16,
    pub result_label: String,
    pub label_available_after_utc: String,
    pub total_goals: u16,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedEventRowV621 {
    pub source_id: String,
    pub fixture_id: String,
    pub event_type: String,
    pub team_name: String,
    pub minute: u16,
    pub player_name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedHistoricalPackV621 {
    pub schema: String,
    pub ready_for_real_model: bool,
    pub fixtures: Vec<NormalizedFixtureRowV621>,
    pub results: Vec<NormalizedResultRowV621>,
    pub events: Vec<NormalizedEventRowV621>,
}

pub fn result_label_v621(home_score: u16, away_score: u16) -> &'static str {
    if home_score > away_score {
        "home_win"
    } else if home_score < away_score {
        "away_win"
    } else {
        "draw"
    }
}

pub fn normalize_sample_fixture_v621(
    source_id: &str,
    fixture_id: &str,
    kickoff_utc: &str,
    home_name: &str,
    away_name: &str,
) -> NormalizedFixtureRowV621 {
    NormalizedFixtureRowV621 {
        source_id: source_id.to_owned(),
        fixture_id: fixture_id.to_owned(),
        kickoff_utc: kickoff_utc.to_owned(),
        home_name: home_name.to_owned(),
        away_name: away_name.to_owned(),
    }
}

pub fn normalize_sample_result_v621(
    source_id: &str,
    fixture_id: &str,
    home_score: u16,
    away_score: u16,
    label_available_after_utc: &str,
) -> NormalizedResultRowV621 {
    NormalizedResultRowV621 {
        source_id: source_id.to_owned(),
        fixture_id: fixture_id.to_owned(),
        home_score,
        away_score,
        result_label: result_label_v621(home_score, away_score).to_owned(),
        label_available_after_utc: label_available_after_utc.to_owned(),
        total_goals: home_score + away_score,
    }
}

pub fn normalize_sample_event_v621(
    source_id: &str,
    fixture_id: &str,
    event_type: &str,
    team_name: &str,
    minute: u16,
    player_name: Option<&str>,
) -> NormalizedEventRowV621 {
    NormalizedEventRowV621 {
        source_id: source_id.to_owned(),
        fixture_id: fixture_id.to_owned(),
        event_type: event_type.to_owned(),
        team_name: team_name.to_owned(),
        minute,
        player_name: player_name.map(str::to_owned),
    }
}

pub fn build_normalized_historical_pack_v621(
    fixtures: Vec<NormalizedFixtureRowV621>,
    results: Vec<NormalizedResultRowV621>,
    events: Vec<NormalizedEventRowV621>,
) -> NormalizedHistoricalPackV621 {
    NormalizedHistoricalPackV621 {
        schema: "omnibet.normalized_historical_pack.v621".to_owned(),
        ready_for_real_model: false,
        fixtures,
        results,
        events,
    }
}

pub fn validate_normalized_pack_v621(pack: &NormalizedHistoricalPackV621) -> Result<(), String> {
    if pack.ready_for_real_model {
        return Err("v621 adapter normalizer must not mark sample packs ready for real model".to_owned());
    }
    if pack.fixtures.is_empty() {
        return Err("normalized pack must include at least one fixture row".to_owned());
    }
    if pack.results.is_empty() {
        return Err("normalized pack must include at least one result row".to_owned());
    }
    for fixture in &pack.fixtures {
        if fixture.source_id.is_empty()
            || fixture.fixture_id.is_empty()
            || fixture.kickoff_utc.is_empty()
            || fixture.home_name.is_empty()
            || fixture.away_name.is_empty()
        {
            return Err(format!("fixture row has missing fields: {}", fixture.fixture_id));
        }
    }
    for result in &pack.results {
        if result.source_id.is_empty()
            || result.fixture_id.is_empty()
            || result.result_label.is_empty()
            || result.label_available_after_utc.is_empty()
        {
            return Err(format!("result row has missing fields: {}", result.fixture_id));
        }
    }
    for event in &pack.events {
        if event.source_id.is_empty()
            || event.fixture_id.is_empty()
            || event.event_type.is_empty()
            || event.team_name.is_empty()
        {
            return Err(format!("event row has missing fields: {}", event.fixture_id));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn result_labels_are_deterministic_v621() {
        assert_eq!(result_label_v621(2, 1), "home_win");
        assert_eq!(result_label_v621(0, 1), "away_win");
        assert_eq!(result_label_v621(1, 1), "draw");
    }

    #[test]
    fn normalized_pack_stays_preview_only_v621() {
        let fixture = normalize_sample_fixture_v621(
            "csv_match_sample",
            "csv-brazil-japan-2026-06-29",
            "2026-06-29T00:00:00Z",
            "Brazil",
            "Japan",
        );
        let result = normalize_sample_result_v621(
            "csv_match_sample",
            "csv-brazil-japan-2026-06-29",
            2,
            1,
            "2026-06-29T23:59:00Z",
        );
        let event = normalize_sample_event_v621(
            "json_event_sample",
            "sample-brazil-japan-20260629",
            "Shot",
            "Brazil",
            12,
            Some("Brazil Player A"),
        );
        let pack = build_normalized_historical_pack_v621(vec![fixture], vec![result], vec![event]);
        assert_eq!(pack.schema, "omnibet.normalized_historical_pack.v621");
        assert!(!pack.ready_for_real_model);
        validate_normalized_pack_v621(&pack).unwrap();
    }
}
