# v79-v86 Competition-Aware Core and Rust Migration Skeleton

This phase fixes a major modelling gap: forecasts must be competition-aware.

## v79 competition registry

Adds a competition registry with:

```text
competition_id
name
country
tier
home-edge prior
goal-rate prior
train_separately
calibrate_separately
```

The initial offline registry includes:

```text
eng_premier
esp_laliga
ita_serie_a
ger_bundesliga
fra_ligue1
int_world
```

## v80 competition-aware historical rows

The compact smoke generates over 1,000 deterministic historical rows with `competition_id` included on every row.

Training rows preserve pre-event feature boundaries and labels.

## v81-v82 per-competition priors, calibration, and rolling evaluation

The evaluation compares:

```text
global_baseline
global_scorecard
competition_prior_scorecard
competition_tuned_scorecard
```

It reports global and per-competition metrics:

```text
Brier score
log loss
accuracy at 0.5
expected calibration error
```

## v83 source coverage matrix

The code-facing matrix uses neutral source IDs. The human planning map is:

```text
OpenFootball / football.json
football-data CSV
football-data.org
StatsBomb Open Data
Understat-style xG source
API-Football-style fixture/state source
The Odds API-style market source
Flashscore reference layer
Sofascore reference layer
Superbet reference layer
OddsPortal reference layer
Betfair exchange reference layer
Pinnacle reference layer
FBref reference layer
worldfootball.net reference layer
```

Policy:

```text
manual/permitted snapshots first
no website automation in CI
no credential values in artifacts
no production mapping mutation
```

## v84 adapter contracts

Adds contracts for historical result rows and market snapshot rows.

Required historical result fields:

```text
source_id
competition_id
season
kickoff_utc
home_name
away_name
home_score
away_score
source_event_id
payload_sha256
```

## v85 Rust eval/calibration skeleton

Adds:

```text
rust-core/src/competition_eval.rs
```

This starts the Rust migration for core evaluation/calibration structs and metrics.

## v86 Rust report reader skeleton

Adds:

```text
rust-core/src/competition_report.rs
```

This starts the Rust migration for model-lab report loading/validation.

## Desktop sample

Adds:

```text
tauri-app/src/competition-lab.sample.json
```

## Smoke

```bash
python python_lab/competition_core_smoke.py \
  --root . \
  --out-dir build/competition_phase_v79_v86 \
  --ui-sample tauri-app/src/competition-lab.sample.json \
  --out reports/ci_v79_v86_competition_core.json
```

## Safety

```text
offline CI only
no credential values
no live source calls
no website automation
no recommendation output
no production mapping mutation
```
