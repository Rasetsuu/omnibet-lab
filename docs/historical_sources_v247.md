# v247 Historical Sources

v247 adds the offline historical source manifest step after the v246 import plan.

It still does not ingest data.

## Input

```text
omnibet.historical_import_plan_preview.v246
```

## Output

```text
omnibet.historical_source_file_manifest.v247
```

## Expected manifest

```text
source entries: 6
total declared rows: 600
offline only: true
network calls allowed: false
paper only: true
import allowed now: false
```

## Validated per entry

```text
task id exists in v246 plan
window/source metadata matches plan
snapshot cutoff matches plan
relative path is safe
codec is supported
row count is non-zero
sha256 has valid shape
point-in-time timestamp marker is present
identity mapping is required
odds source requires market mapping
no credentials stored
no network calls performed
import still disabled
```

## Why import is still disabled

This manifest validates declared local source candidates only. Real import requires a later step that checks actual files exist and hashes them locally.

## Next step

v248 should add real local file existence/hash verification for these source candidates, still without promoting anything into training data.
