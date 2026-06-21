# v248 Historical Source Verification

v248 verifies declared local historical source files before any import work.

It still does not ingest data and does not promote rows into training/evaluation datasets.

## Input

```text
omnibet.historical_source_file_manifest.v247
```

## Output

```text
omnibet.historical_source_verification_report.v248
```

## Verification checks

```text
safe relative path
file exists
path is a regular file
SHA-256 matches manifest
row count matches manifest
unsafe flags rejected
unsupported codecs rejected
```

## Supported codecs

```text
csv
json
jsonl.gzip
```

The current Rust tests create temporary local files and verify actual file reads, SHA-256 hashes, and row counts.

## Safety

Even after successful verification:

```text
import_allowed_now: false
promotion_allowed: false
```

Verification means the declared local source candidates are physically present and match their manifest. It is not ingestion, not silver/gold promotion, and not training-data approval.

## Next step

v249 should add a bronze candidate preview writer that can read verified local source rows into a quarantined candidate cache, still disabled for training and evaluation until schema/settlement checks pass.
