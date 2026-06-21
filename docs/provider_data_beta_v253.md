# v253 Provider Data Beta Slice

v253 is a beta-oriented provider/data batch.

It defines which provider and historical data sources are needed for the actual prediction/betting research beta.

## Goals

```text
provider adapter readiness matrix
credential capability contract
historical coverage targets
desktop source-panel contract
```

## Priority-one beta sources

```text
the_odds_api
api_football
```

These are treated as the first live-adapter targets, but CI remains offline and no credentials are stored in the repository.

## Additional historical/source candidates

```text
football_data_co_uk
football_data_org
statsbomb_open_data
```

These help backfill results, closing odds, fixture context, and event-context research.

## Credential policy

Credentials are declared only as environment variable names.

```text
THE_ODDS_API_KEY
API_FOOTBALL_KEY
FOOTBALL_DATA_ORG_KEY
```

No API keys or secrets belong in the repository.

## Historical coverage targets

```text
tier1_league_backfill:
  EPL, LaLiga, SerieA, Bundesliga, Ligue1
  minimum 5 seasons
  results + odds required

international_tournament_backfill:
  WorldCup, Euro, CopaAmerica
  minimum 3 seasons
  results + odds + lineup/event context required
```

## Desktop source surface

The market terminal/source panel should show:

```text
provider health
credential status
historical coverage
adapter gaps
```

Manual manifest import is allowed, but live fetch buttons stay disabled until adapter smokes and user-provided credentials are handled safely.

## Safety

```text
paper_only: true
network_calls_allowed_in_ci: false
credentials_stored_in_repo: false
ci_live_calls_allowed: false
```

## Next beta-oriented batch

v254 should add offline adapter request/response contracts and local fixture files for the priority-one provider targets:

```text
The Odds API odds snapshot contract
API-Football fixtures/results/events contract
provider response metadata contract
adapter health report contract
```
