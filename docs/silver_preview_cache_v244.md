# v244 Silver Preview Cache

v244 materializes the v243 silver fact preview bundle into a verifiable local artifact.

It mirrors the bronze cache pattern but stays in preview-only silver space.

## Output layout

```text
build/silver_preview_cache/v244_offline_sample/
  manifest.json
  tables/
    silver_fact_preview_rows.jsonl.gz
```

## Expected offline cache

```text
tables: 1
table name: silver_fact_preview_rows
total rows: 22
market fact rows: 7
identity link rows: 15
preview only: true
training dataset promotion allowed: false
credential values stored: false
network calls performed: false
```

## Verification

The verifier checks:

```text
manifest schema
codec jsonl.gzip
manifest sha256
table sha256
table row count
total row count
preview-only flag
training-promotion flag
credential/network flags
```

## Safety

```text
preview only
not training data
no network calls
no credentials stored
```

## Why this matters

This is the first persistent silver-style artifact. It proves that clean mapped preview facts can be written, hashed, verified, and read back before we scale to real historical data.

## Next step

v245 should introduce historical import contracts for larger fixture/odds datasets, while preserving point-in-time boundaries and the same review gates.
