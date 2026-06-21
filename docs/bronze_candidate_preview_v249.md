# v249 Bronze Candidate Preview

v249 builds a quarantined preview bundle from verified local historical source files.

It does not promote rows to bronze storage yet.

## Inputs

```text
omnibet.historical_source_file_manifest.v247
omnibet.historical_source_verification_report.v248
```

## Output

```text
omnibet.bronze_candidate_preview_bundle.v249
```

## Row shape

Each preview row includes:

```text
row id
task id
source id
source kind
relative path
row number
raw line SHA-256
quarantine flags
```

## Safety

Every bundle and row keeps:

```text
quarantine_only: true
import_allowed_now: false
promotion_allowed: false
evaluation_allowed: false
training_dataset_promotion_allowed: false
```

If v248 verification fails, v249 emits no preview rows.

## Why this matters

v248 proved files exist and match their declared manifest.

v249 creates a tiny inspectable preview of what would be read from those files, without letting those rows enter real bronze/silver/gold/evaluation/training paths yet.

## Next step

v250 should add schema classification for quarantined preview rows: fixture/result rows, odds snapshot rows, and lineup/event-context rows. Rows that cannot be classified must stay quarantined with review reasons.
