# v266-v270 Storage V2 Compression Foundation

This batched phase turns the older v233 Storage V2 roadmap into a stricter Rust-facing storage/compression contract.

It does not ingest large real datasets yet, does not train models, and does not perform provider calls. It defines the stable shapes needed before the historical dataset and model phases.

## Included versions

```text
v266 JSONL.Zstd raw snapshot contract
v267 Parquet.Zstd Silver/Gold metadata contract
v268 Rust provider cache manifest direction
v269 Silver/Gold writer migration plan
v270 walk-forward dataset loader shape
```

## Compatibility rule

The current small pack path remains valid:

```text
jsonl.gzip for CI and small runtime packs
```

The new large-data direction is:

```text
Bronze raw snapshots      -> jsonl.zstd / json.zstd, temporary
Silver canonical facts    -> parquet.zstd, long-term
Gold training features    -> parquet.zstd, long-term
Recent runtime cache      -> SQLite or small JSONL.GZ
```

## v266 - JSONL.Zstd raw snapshot contract

Bronze raw snapshots are for temporary audit/replay only.

Required manifest fields include:

```text
snapshot_id
source_id
request_kind
captured_at
observed_at
payload_sha256
payload_path
codec
compressed_bytes
uncompressed_bytes
row_count
```

Policy:

```text
retention_days_default: 30
delete_raw_after_verified_promotion: true
credential_values_allowed: false
```

## v267 - Parquet.Zstd Silver/Gold metadata contract

Silver facts and Gold features use `parquet.zstd` for long-term storage.

Silver partition keys:

```text
sport
competition_id
season_id
snapshot_date
```

Gold partition keys:

```text
sport
market_family
feature_version
prediction_date
```

Silver/Gold metadata must include row counts, content hashes, lineage inputs, partition summaries, and leakage-boundary reports.

## v268 - Rust provider cache manifest direction

Provider cache manifests target Rust as the stable runtime.

Required fields include:

```text
cache_id
provider
source_role
captured_at
observed_at_min
observed_at_max
row_count
codec
content_sha256
lineage_inputs
promotion_state
```

Forbidden fields:

```text
api_key
secret
bearer_token
credential_value
```

Python remains allowed for provider prototypes and notebooks before contracts stabilize.

## v269 - Silver/Gold writer migration plan

Silver writer inputs:

```text
verified_bronze_snapshot_manifest
identity_mapping_review
market_mapping_review
```

Gold writer inputs:

```text
silver_fact_manifest
feature_recipe_manifest
prediction_time_windows
settlement_manifest
```

Writer outputs:

```text
table_manifest
row_counts
content_hashes
partition_summary
leakage_boundary_report
```

## v270 - Walk-forward dataset loader shape

The dataset loader targets Rust and forbids random splits.

Required window fields:

```text
train_start
train_end
validation_start
validation_end
test_start
test_end
prediction_time_column
label_available_after_column
```

Required safety checks:

```text
feature_observed_at_lte_prediction_time
label_created_after_settlement
no_random_shuffle_split
market_family_specific_validation
```

## Rust module

The Rust-facing validation lives in:

```text
rust-core/src/storage_v2_compression_v266.rs
```

It parses and validates:

```text
configs/storage_v2_compression.v266_v270.json
```

## Files

```text
configs/storage_v2_compression.v266_v270.json
data/storage_v2/v266_v270/storage_v2_compression.sample.json
docs/storage_v2_compression_v266_v270.md
rust-core/src/storage_v2_compression_v266.rs
python_lab/storage_v2_compression_smoke.py
.github/workflows/v266_v270_storage_v2_compression.yml
```

## Acceptance

v266-v270 is accepted when:

```text
jsonl.gzip compatibility remains preserved
Bronze raw snapshots use zstd and are temporary
Silver/Gold use parquet.zstd and are long-term
provider cache manifests forbid credentials
Silver/Gold writer plan targets Rust
walk-forward dataset loader forbids random splits
content hashes and row counts are required
Rust module parses/validates the contract
Python smoke validates the contract/sample/docs/module/workflow
```
