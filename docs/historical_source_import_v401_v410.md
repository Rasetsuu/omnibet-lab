# v401-v410 Historical Source Import

This phase starts the real-data pivot for OmniBet Lab.

It defines the first safe local historical source import layer for football fixtures, odds snapshots, settlement labels, and provider/team identity mappings.

It still does not train a model. The output is only a validation/import report that can later feed Bronze/Silver/Gold materialization.

## Included versions

```text
v401 historical import source contract
v402 local file manifest schema
v403 fixture history row schema
v404 odds history row schema
v405 settlement/result history row schema
v406 provider/team identity mapping preview
v407 import validation report
v408 Rust historical import validator
v409 CI historical import smoke
v410 historical import docs
```

## Input model

The phase accepts local files only:

```text
json
jsonl
csv
```

The bundled sample pack is JSON and lives under:

```text
data/historical/v401_v410/
```

Files:

```text
historical_import.sample.json
fixtures.sample.json
odds.sample.json
settlements.sample.json
identity_map.sample.json
```

## Fixture rows

Fixture history rows include:

```text
fixture_id
source_id
competition
season
kickoff_utc
home_team_raw
away_team_raw
home_team_canonical_id
away_team_canonical_id
final_home_score
final_away_score
result_status
```

## Odds rows

Odds history rows include:

```text
fixture_id
source_id
market_family
market_id
selection_id
selection_raw
bookmaker
captured_at_utc
decimal_odds
is_closing_snapshot
```

Rules:

```text
decimal_odds must be > 1.0
closing/prematch odds must be captured before kickoff
odds fixture_id must exist in fixtures
```

## Settlement rows

Settlement history rows include:

```text
fixture_id
market_family
selection_id
settled_at_utc
settlement_result
label_available_after_utc
```

Rules:

```text
settlement fixture_id must exist in fixtures
label_available_after_utc must not be before kickoff
settlement_result must be win/loss/push/void
```

## Identity rows

Identity mapping rows include:

```text
entity_type
source_id
raw_name
canonical_id
canonical_name
confidence
review_status
```

Low-confidence identity mappings must be marked `needs_review`.

## Rust validator

The Rust module is:

```text
rust-core/src/historical_source_import_v401.rs
```

It provides:

```text
HistoricalFixtureRowV401
HistoricalOddsRowV401
HistoricalSettlementRowV401
HistoricalIdentityRowV401
HistoricalImportValidationReportV401
validate_historical_import_contract
validate_historical_import_pack
load_and_validate_historical_import
write_historical_import_validation_report
```

## Validation output

The validation report schema is:

```text
omnibet.historical_import_validation_report.v401_v410
```

Important fields:

```text
paper_only = true
status = validated_for_materialization or blocked_import_validation
ready_for_materialization = true/false
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

Even if import validation passes:

```text
ready_for_training = false
```

Training only becomes possible after later materialization, no-leak feature building, walk-forward evaluation, baseline comparison, calibration, and CLV analysis.

## Safety invariants

```text
local files only
no live provider calls
no credential values
no real-money recommendations
no model training in v401-v410
no random train/test split
labels available only after fixtures
prematch odds captured before kickoff
identity ambiguity must be reviewed
```

## Next

After this phase, the next natural step is:

```text
v411-v420 Bronze/Silver/Gold materialization from historical local files
```

That should turn validated historical source rows into materialized local datasets, still without training.
