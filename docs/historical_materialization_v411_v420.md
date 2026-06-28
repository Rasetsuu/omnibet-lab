# v411-v420 Historical Materialization

This phase turns validated local historical source rows into materialized preview layers.

It consumes the v401-v410 local historical import sample pack and produces Bronze, Silver, and Gold preview table shapes. It still does not train a model.

## Included versions

```text
v411 Bronze fixture import table
v412 Bronze odds snapshot import table
v413 Bronze settlement import table
v414 identity mapping application
v415 Silver normalized fixture table
v416 Silver normalized odds table
v417 Gold evaluation candidate preview
v418 materialization manifest writer
v419 CI materialization smoke
v420 materialization docs
```

## Inputs

The source inputs remain local files only:

```text
data/historical/v401_v410/historical_import.sample.json
data/historical/v401_v410/fixtures.sample.json
data/historical/v401_v410/odds.sample.json
data/historical/v401_v410/settlements.sample.json
data/historical/v401_v410/identity_map.sample.json
```

The materializer depends on the v401-v410 import validation report being safe for materialization.

## Bronze previews

Bronze preserves raw provider-facing fields for auditability.

```text
bronze_fixtures_v411
bronze_odds_v412
bronze_settlements_v413
```

Preview output paths:

```text
reports/materialized/v411_v420/bronze_fixtures.preview.json
reports/materialized/v411_v420/bronze_odds.preview.json
reports/materialized/v411_v420/bronze_settlements.preview.json
```

## Silver previews

Silver applies identity mapping and normalizes fixture/odds table shape.

```text
silver_fixtures_v415
silver_odds_v416
```

Preview output paths:

```text
reports/materialized/v411_v420/silver_fixtures.preview.json
reports/materialized/v411_v420/silver_odds.preview.json
```

Silver fixture rows contain canonical team ids and names. Silver odds rows contain a `no_vig_group_key` so later no-vig calculations can group selections from the same bookmaker, market, fixture, and capture timestamp.

## Gold preview

Gold creates evaluation candidate rows only when an odds row can be joined to a settlement row.

```text
gold_evaluation_candidates_v417
```

Preview output path:

```text
reports/materialized/v411_v420/gold_evaluation_candidates.preview.json
```

Gold candidate rows contain:

```text
candidate_id
fixture_id
prediction_time_utc
label_available_after_utc
market_family
selection_id
decimal_odds
settlement_result
feature_leakage_safe
```

The `feature_leakage_safe` flag is true only when the label is available after the prediction time.

## Manifest

The materialization manifest is:

```text
reports/materialized/v411_v420/materialization_manifest.json
```

It records Bronze, Silver, and Gold table summaries and keeps the future storage direction explicit:

```text
preferred_large_scale_codec = jsonl.zstd
future_large_scale_codec = parquet.zstd
```

Content hashes are intentionally marked as not present in this preview. A later storage writer phase should add stable hashes for real large-scale materialized files.

## Safety invariants

```text
paper_only = true
local_first = true
no live provider calls
no credential values
no recommendation output
ready_for_walk_forward may become true
ready_for_training = false
trust_status = sample_only
```

Even when Bronze/Silver/Gold previews are successfully built:

```text
ready_for_training = false
```

Training remains blocked until no-leak walk-forward evaluation, baselines, calibration, and paper CLV gates pass on real materialized data.

## Rust module

```text
rust-core/src/historical_materialization_v411.rs
```

Main public helpers:

```text
parse_historical_materialization_contract_v411
validate_historical_materialization_contract_v411
build_bronze_fixture_rows_v411
build_bronze_odds_rows_v411
build_bronze_settlement_rows_v411
build_silver_fixture_rows_v411
build_silver_odds_rows_v411
build_gold_candidate_rows_v411
build_historical_materialization_report_v411
write_historical_materialization_preview_v411
```

The v411 helper names are intentionally unique to avoid Rust glob re-export ambiguity with earlier historical modules.

## Next

After v411-v420, the natural next phase is:

```text
v421-v430 historical materialization command bridge and generated artifacts
```

That would expose a local command path for writing materialized previews and loading them into desktop/report views.
