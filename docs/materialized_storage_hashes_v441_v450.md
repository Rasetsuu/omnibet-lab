# v441-v450 Materialized Storage Hashes

This phase adds storage integrity and compression for generated historical materialization artifacts.

It consumes v421-v430 generated JSON artifacts and writes:

```text
reports/materialized/v441_v450/materialized_storage_manifest.json
reports/materialized/v441_v450/materialized_storage_verification_report.json
reports/materialized/v441_v450/compressed/*.zst
```

## Included versions

```text
v441 materialized artifact hash manifest contract
v442 SHA-256 for generated Bronze artifacts
v443 SHA-256 for generated Silver artifacts
v444 SHA-256 for generated Gold artifacts
v445 Zstd compressed artifact copy writer
v446 compressed size ratio report
v447 storage manifest verification report
v448 desktop storage manifest contract placeholder
v449 CI storage hash smoke
v450 storage hash docs
```

## Input artifacts

The storage hasher expects the v421-v430 command output directory:

```text
reports/materialized/v421_v430/
```

Input files:

```text
bronze_fixtures.generated.json
bronze_odds.generated.json
bronze_settlements.generated.json
silver_fixtures.generated.json
silver_odds.generated.json
gold_evaluation_candidates.generated.json
materialization_manifest.json
command_result.json
```

## Command

```text
omnibet-materialized-storage-hasher
```

Example:

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-materialized-storage-hasher -- \
  --root . \
  --artifact-dir reports/materialized/v421_v430 \
  --out-dir reports/materialized/v441_v450/compressed \
  --manifest-out reports/materialized/v441_v450/materialized_storage_manifest.json \
  --verification-out reports/materialized/v441_v450/materialized_storage_verification_report.json \
  --run-id ci_v441_v450
```

## Manifest record

Each artifact record includes:

```text
artifact_id
source_path
compressed_path
codec
source_bytes
compressed_bytes
sha256
compressed_sha256
compression_ratio
status
```

## Compression

The current generated artifact copy format is:

```text
zstd
```

The generated copy extension is:

```text
.zst
```

Parquet remains a future table-schema phase. This batch keeps the generated JSON artifacts as the canonical preview format and adds compressed copies plus hashes around them.

## Safety locks

The storage layer does not change trust or training state:

```text
paper_only = true
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

## Why this matters

Before this phase, v421 generated JSON artifacts but did not prove stable content identity. v441 adds:

```text
SHA-256 source hashes
SHA-256 compressed hashes
compressed size reporting
manifest verification
```

This is a prerequisite before scaling beyond tiny samples and before a desktop storage panel can trust artifact freshness.

## Next

The next phase should expose the storage manifest in the desktop historical materialization page:

```text
v451-v460 materialized storage desktop panel
```

After that, the project can move toward real local historical file adapter UX and larger historical data ingestion.
