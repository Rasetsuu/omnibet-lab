# v236 Bronze Snapshot Cache

v236 materializes the offline provider parser outputs into a verifiable bronze cache.

It is still offline-only and credential-free. No live provider calls are introduced.

## Input

The cache starts from the v235 offline sample parsers:

```text
The Odds API-style event markets
API-Football-style live state
```

## Output layout

The Rust writer produces:

```text
build/bronze_cache/v236_offline_samples/
  manifest.json
  tables/
    source_manifests.jsonl.gz
    fixtures.jsonl.gz
    odds.jsonl.gz
    market_discovery.jsonl.gz
    events.jsonl.gz
    lineups.jsonl.gz
    statistics.jsonl.gz
```

## Tables

Expected demo rows:

```text
source_manifests: 2
fixtures: 2
odds: 17
market_discovery: 8
events: 4
lineups: 8
statistics: 12
TOTAL: 53
```

## Manifest

The manifest records:

```text
schema
cache_id
created_at
codec
layer
source_ids
source payload manifests
table paths
row counts
uncompressed JSONL byte counts
compressed byte counts
table SHA-256 hashes
manifest SHA-256
credential safety flags
network safety flags
```

## CLI

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-bronze-cache -- \
  --out build/bronze_cache/v236_offline_samples \
  --cache-id v236_offline_provider_samples \
  --created-at 2026-06-20T00:00:00Z
```

The CLI parses the saved provider samples, writes the cache, verifies it, and prints a JSON report.

## Safety

v236 keeps the same safety line as v234/v235:

```text
no provider credentials required
credential values never stored
credential values never displayed
no network calls in CI
unknown provider markets remain review-only
```

The `special_combo_unknown` sample market must remain flagged with `needs_mapping_review=true` inside the materialized `market_discovery` cache table.

## Why this matters

This is the bridge from sample parsers to actual storage:

```text
saved provider payload
→ typed Rust parser rows
→ bronze JSONL.GZ cache
→ verifiable manifest
→ future silver canonical facts
```

The next step is to add the first canonical identity and market mapping registry so bronze rows can be promoted into silver facts without fuzzy dangerous auto-merges.
