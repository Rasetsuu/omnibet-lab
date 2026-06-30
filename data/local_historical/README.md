# Local Historical Intake

Put user-provided completed-data packs here when testing locally.

This folder is intentionally local-first.

## Supported first shapes

```text
*.csv   football-data shaped match rows
*.json  openfootball shaped match rows or event-shaped rows
```

## Rules

```text
completed rows only
no credentials
no live network calls in CI
no secrets
no raw private provider dumps
```

## Current repo policy

The repository keeps this folder as an intake target, but large real datasets should normally stay outside git or be added only as small approved samples.

The scanner reports counts and gate status; it does not train anything.
