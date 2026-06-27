# v271-v280 Historical Dataset Foundation

This batched phase moves OmniBet from storage/compression shape into historical dataset build planning.

It does not ingest large real datasets yet, does not train models, and does not call live providers in CI. It defines the source coverage, import targets, manifest bundle, settlement/closing-odds targets, readiness report, and first leak-safe dataset build plan needed before model training.

## Included versions

```text
v271 historical source coverage matrix
v272 league/tournament import window targets
v273 historical source manifest bundle
v274 settlement and closing-odds target contract
v275 coverage/readiness report
v276-v280 first leak-safe dataset build plan
```

## v271 - Historical source coverage matrix

Primary source roles are now explicit:

```text
football_data_co_uk     -> historical results, match stats, bookmaker odds, closing-odds proxy
api_football            -> fixtures, results, lineups, events, match stats, live state
the_odds_api            -> bookmaker odds, market snapshots, odds freshness
statsbomb_open_data     -> events, lineups, players, shots for limited open competitions
football_data_org       -> fixtures, results, competitions, standings
sportmonks_candidate    -> paid coverage candidate for fixtures, livescores, lineups, events, statistics
betfair_historical      -> exchange prices, traded volume, market movement candidate
openfootball/openligadb -> open results backfill
international_results   -> national-team and tournament history backfill
```

Credential values remain forbidden. Sources that require credentials are allowed only as capability/manifest targets until safe local credential handling exists.

## v272 - League and tournament targets

Primary league target:

```text
top 5 European leagues
minimum_seasons: 5
required: fixtures, results, odds, settlements
preferred: lineups, events, match_stats, closing_odds
```

Tournament target:

```text
World Cup, Euro, Copa America, AFCON, Asian Cup
minimum_tournament_editions: 3
required: fixtures, results, settlements
preferred: lineups, events, odds, closing_odds
```

Secondary European leagues are defined as lower-priority backfill targets.

## v273 - Historical source manifest bundle

Each local source manifest must include:

```text
source_id
provider
source_role
license_notes
local_path
expected_codec
expected_columns
season_start
season_end
sha256
row_count
observed_at_policy
promotion_target
```

Allowed codecs:

```text
csv
json
jsonl.gzip
jsonl.zstd
parquet.zstd
```

Promotion targets:

```text
bronze_raw_snapshot
silver_candidate
gold_feature_candidate
```

## v274 - Settlement and closing-odds target contract

Initial market families:

```text
1x2
totals
btts
team_totals
double_chance
draw_no_bet
```

Settlement labels must be created only after settlement.

Closing odds rows must track:

```text
canonical_fixture_id
market_key
selection_key
bookmaker
closing_price_decimal
captured_at
source_id
```

Paper CLV is required before claiming market quality.

## v275 - Coverage/readiness report

Readiness gates include:

```text
minimum_ready_rows: 1000
minimum_completed_seasons_per_primary_league: 3
minimum_odds_coverage_ratio: 0.6
minimum_settlement_coverage_ratio: 0.95
```

Known blocker reasons:

```text
missing_local_source_file
hash_mismatch
insufficient_season_window
missing_odds_columns
missing_settlement_labels
identity_mapping_required
market_mapping_required
```

## v276-v280 - First leak-safe dataset build plan

The first dataset build plan targets Rust and Storage V2 compression.

Stages:

```text
verify_local_source_manifests
materialize_bronze_candidates
classify_bronze_rows
run_identity_mapping_review
run_market_mapping_review
write_silver_candidates
derive_gold_feature_candidates
attach_settlement_labels_after_final
emit_coverage_readiness_report
```

Forbidden actions:

```text
random_split
train_on_unsettled_games
store_credentials
live_provider_calls_in_ci
```

This phase intentionally does not claim training readiness.

## Rust module

Rust-facing validation lives in:

```text
rust-core/src/historical_dataset_v271.rs
```

It parses and validates:

```text
configs/historical_dataset_foundation.v271_v280.json
```

## Files

```text
configs/historical_dataset_foundation.v271_v280.json
data/historical/v271_v280/historical_dataset_foundation.sample.json
docs/historical_dataset_foundation_v271_v280.md
rust-core/src/historical_dataset_v271.rs
python_lab/historical_dataset_foundation_smoke.py
.github/workflows/v271_v280_historical_dataset_foundation.yml
```

## Acceptance

v271-v280 is accepted when:

```text
coverage matrix includes primary historical/fixture/odds/event sources
league and tournament windows are defined
manifest bundle requires hashes, row counts, lineage, and observed-at policy
settlement and closing-odds targets are defined
coverage readiness thresholds are explicit
dataset build plan preserves no-leak boundaries
Rust module parses/validates the contract
Python smoke validates contract/sample/docs/module/workflow
```
