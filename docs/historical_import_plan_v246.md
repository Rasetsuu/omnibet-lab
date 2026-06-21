# v246 Historical Import Plan Preview

v246 turns the v245 historical import contract into an offline import plan.

It still does not fetch or ingest production data.

## Input

```text
omnibet.historical_import_contract.v245
```

## Output

```text
omnibet.historical_import_plan_preview.v246
```

## Expected plan

The current contract contains:

```text
windows: 2
required source classes: 3
total tasks: 6
```

The task matrix is:

```text
2 windows × 3 required source classes
```

Each task includes:

```text
window id
source id
source kind
competition id
season
start/end dates
snapshot cutoff UTC
point-in-time timestamp requirement
identity mapping requirement
market mapping requirement for odds
credential persistence rule
required next artifact
```

## Safety

```text
offline only
network calls disabled
paper only
import_allowed_now: false
```

The plan does not allow importing yet. The next required artifact is:

```text
offline_file_manifest_with_sha256_and_row_count
```

## Why this matters

v245 said what a safe historical import must prove.

v246 turns that into a concrete task list so the next step can attach actual local files and verify row counts/hashes before anything becomes a bronze candidate.

## Next step

v247 should add the offline historical file manifest contract: local file references, source kind, row counts, SHA-256, snapshot cutoffs, and validation against this plan.
