# v260-v265 Live Source + Prediction Context Bridge

This document locks the next OmniBet phase after v259 so the project does not drift into either a simple score predictor or a premature final GUI polish pass.

The phase goal is to connect the current provider/source-terminal foundation to the future prediction market terminal:

```text
source terminal / provider health
-> upcoming and live fixture awareness
-> odds snapshot awareness
-> live snapshot storage and settlement loop
-> prediction-ready match context bundle
-> later Rust Storage V2, training, and market terminal MVP
```

## Current baseline

Latest merged functional baseline:

```text
v259 source generate-refresh flow
```

v259 lets the desktop source view run the local source report generation workflow and refresh the report view from the GUI.

This phase starts from that point. It does not replace the final GUI plan. It builds the missing bridge that the final GUI and training stack need.

## Non-negotiable rules

```text
paper_only: true
windows_linux_required: true
ci_live_provider_calls_allowed: false
secrets_in_repo_allowed: false
raw_provider_payloads_are_not_training_data: true
random_train_test_splits_allowed: false
same_game_legs_independent_by_default: false
```

OmniBet remains a local-first research tool. No GUI wording should imply real-money betting confidence. Every prediction-facing output must remain paper-only until historical validation, calibration, no-vig baseline comparison, and CLV evidence exist.

## Python and Rust rule

Python remains allowed for:

```text
research prototypes
feature experiments
model experiments
quick provider exploration
paper ledger analysis
CLV/no-vig reports
local smoke helpers
```

Rust is the target for stable runtime paths:

```text
provider contracts
normalized adapters
storage manifests
bronze/silver/gold writers
source reports
prediction-ready context bundles
Tauri command-facing CLIs
walk-forward dataset loading
```

The rule for this phase:

```text
prototype fast when needed, then freeze stable contracts into Rust.
```

## Storage and compression direction

Small deterministic CI/runtime samples may continue to use JSONL.GZ packs.

Large historical/training paths should move toward Storage V2 later:

```text
Bronze raw snapshots      -> json.zstd / jsonl.zstd, temporary
Silver canonical facts    -> parquet.zstd, long-term
Gold training features    -> parquet.zstd, long-term
Recent runtime cache      -> SQLite or small local JSONL.GZ
Model artifacts           -> model binary + JSON manifest
```

This phase should not force the full compression migration yet, but it must not design contracts that block it.

## Training data rule

The model must not train directly on random site dumps or raw API payloads.

The intended training flow is:

```text
raw provider/source payloads
-> Bronze raw snapshots for audit/replay
-> Silver canonical facts
-> Gold leak-safe training features
-> walk-forward training/evaluation
-> paper-only predictions and CLV tracking
```

For live/upcoming games:

```text
before match: collect fixture/context/odds snapshot and save prediction snapshot
during match: collect live state and odds snapshots with timestamps
after match: attach final settlement labels and promote useful facts/features
later: use completed and settled games for training/evaluation
```

The no-leak rule is:

```text
feature.observed_at <= prediction_time
label.created_after final_or_settled_state
```

Raw Bronze payloads may be deleted or archived after verified promotion. Silver facts, Gold features, settlements, odds snapshots needed for CLV, model manifests, and paper ledger records should be kept long-term in compressed form.

## Provider roles

Priority provider direction remains:

```text
API-Football / API-SPORTS -> fixtures, live state, lineups, events, match stats
The Odds API              -> bookmaker odds, market snapshots, odds freshness
```

Additional or later candidates may include:

```text
Sportmonks                -> richer fixture/live/lineup/event/odds coverage candidate
Betfair Exchange          -> sharper exchange price/liquidity/market movement candidate
football-data.co.uk       -> historical results, odds, closing-price style backfill
football-data.org         -> fixtures/results/competitions source
StatsBomb Open Data       -> event and lineup research where coverage exists
OpenFootball/OpenLigaDB   -> open historical fixture/result support
international result sets -> tournament and national-team backfill
```

The GUI should show provider status and data freshness, not secret values.

## Phase map

### v260 - Source Terminal filters and row details

Make the existing Source Terminal useful for beta work.

Scope:

```text
provider filters
row type filters
readiness filters
blocker/review-reason filters
sample row details
adapter health detail
normalized preview detail
source freshness display
next-action hints
```

Acceptance:

```text
existing v259 generate-refresh flow still works
source report can be filtered locally
row details can be inspected without live provider calls
no credentials or raw secrets are displayed
README/doc links updated
smoke checks added or updated
```

### v261 - Upcoming/live fixture source contract

Define how OmniBet asks what matches exist now and soon.

Scope:

```text
fixture date-range request contract
live fixture request contract
normalized fixture/live row schema
offline provider samples
status/phase normalization
fixture freshness metadata
lineup/event/stat availability flags
```

Normalized rows should support:

```text
provider
provider_fixture_id
canonical_fixture_id when mapped
competition
season
home_team
away_team
kickoff_time
status
phase
minute
score
lineup_available
event_data_available
stats_available
observed_at
captured_at
```

Acceptance:

```text
offline fixture/live samples parse deterministically
Rust contracts compile and test
no CI live calls
source report can summarize fixture/live readiness
```

### v262 - Odds snapshot source contract

Define bookmaker/market snapshot inputs for prediction and CLV.

Scope:

```text
odds snapshot request contract
odds by fixture/event id
market availability rows
bookmaker/market/selection normalization
in-play flag
last_update and freshness status
missing odds reasons
```

Normalized rows should support:

```text
provider
provider_event_id
canonical_fixture_id when mapped
bookmaker
market_key
selection_key
price_decimal
is_in_play
market_status
last_update
observed_at
captured_at
```

Acceptance:

```text
offline odds samples parse deterministically
market aliases map through the canonical market registry
unknown markets are quarantined/reviewed, not silently promoted
source report can summarize odds readiness
```

### v263 - Desktop Upcoming/Live Matches panel

Add the first GUI bridge toward the final market terminal.

Scope:

```text
Live Now section
Today section
Tomorrow section
Next 3 Days section
competition/provider filters
fixture readiness badges
odds available/missing badge
lineup/event availability badges
source freshness display
```

This should remain offline/sample-first. Credential-gated live fetch buttons can be planned but should stay locked until adapter smokes and secret handling are safe.

Acceptance:

```text
Tauri desktop runs on Windows and Linux paths
panel renders offline generated fixture/live report
no prediction confidence language yet
no live CI calls
```

### v264 - Live snapshot storage and retention contract

Define how live/upcoming games become future training material after settlement.

Scope:

```text
pre-match snapshot schema
live snapshot schema
post-match settlement schema
snapshot manifest
promotion markers
raw Bronze retention/deletion policy
settlement linkage to previous prediction snapshots
```

Acceptance:

```text
snapshots preserve prediction-time boundaries
settlement labels are separate from pre/live features
raw payload retention policy is documented and testable
promoted Silver/Gold records can outlive raw payloads
```

### v265 - Prediction-ready match context bundle

Create the stable object that later model and GUI work can consume.

Scope:

```text
fixture context
team context
player/lineup context when available
live state context
odds snapshot context
market availability context
data freshness context
trust blockers
prediction readiness summary
```

The bundle is not the final model. It is the input contract for future models and the market terminal.

Acceptance:

```text
context bundle can be generated from offline samples
missing data creates explicit blockers, not silent nulls
bundle is suitable for Rust CLIs and Tauri commands
future model training can use the same shape without leakage
```

## After this phase

The next larger phases should be:

```text
v266-v270: Rust Storage V2 and compression migration
v271-v280: historical dataset build and source backfill
v281-v290: leak-free model baselines, calibration, no-vig/CLV paper analysis
v291+: market terminal MVP and paper-only bilet builder
later: player props, full live terminal, final GUI polish
```

## Definition of done for v260-v265

This phase is complete when OmniBet can answer, from safe local/offline or credential-gated inputs:

```text
what matches are live now?
what matches are upcoming soon?
which matches have odds?
which matches have lineups/events/stats?
which rows are prediction-ready?
which rows are blocked and why?
what exact match context would the future model receive?
what data can later be promoted into training after settlement?
```

At the end of this phase, OmniBet should still be paper-only, but it should no longer be just a source/report tool. It should be ready to become a real prediction market terminal.