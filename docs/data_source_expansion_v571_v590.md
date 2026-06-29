# v571-v590 Data Source Expansion

This phase records the source plan before scaling rows.

## Goal

OmniBet needs many settled historical rows before the eval gate can unlock useful engine work.

This phase does not download anything in CI. It only maps candidate data sources, market coverage, gaps, and adapter priority.

## Candidate sources

```text
football_data_csv
statsbomb_open_data
openfootball_json
elo_rating_slot
```

## First priority

```text
football_data_csv
```

Reason: it can provide historical fixture/result rows and price fields in computer-ready CSV form.

## Event and player gaps

The paper market catalog includes corners, cards, free kicks, offsides, shots, shots on target, player passes, fouls, tackles, assists, and bookings.

Those require richer event/player data.

Current source mapping:

```text
corners/cards/set pieces -> future event source
player shots/passes/etc -> statsbomb open data or future player event source
odds value -> football_data_csv first
team history -> football_data_csv or openfootball_json
rating prior -> elo_rating_slot
```

## CI policy

```text
ci_downloads_allowed = false
live_provider_calls_allowed = false
manual import first
cache first
no credentials in repo
```

## Next

```text
v591-v620 adapter samples and historical row pack
v621-v650 Rust runtime migration for stable adapters
```
