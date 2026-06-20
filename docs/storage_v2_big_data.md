# v233 Storage V2 Big Data Roadmap

OmniBet needs to scale from tiny CI/runtime packs to large football training data across many market families: goals, corners, cards, offsides, shots, player props, scorer markets, live state, odds movement, and same-game ticket features.

The current pack format already supports small immutable packs:

```text
jsonl.gzip tables
manifest.json
row counts
compressed byte counts
compression ratios
SHA-256 hashes
Rust verification/readback
```

That remains useful for CI, offline samples, and small runtime bundles.

For large historical data and model training, v233 defines the next storage direction:

```text
Bronze raw snapshots      -> json.zstd / jsonl.zstd, temporary
Silver canonical facts    -> parquet.zstd, long-term
Gold training features    -> parquet.zstd, long-term
Model artifacts           -> model binary + JSON manifest
Recent runtime cache      -> SQLite or small local JSONL.GZ
```

## Bronze raw snapshots

Bronze stores provider payloads for audit/replay only.

Required metadata:

```text
source_id
request_kind
captured_at
observed_at
payload_sha256
payload_path
```

Default retention is 30 days. After promotion into canonical facts and training features, raw payloads should be deleted or archived. API credentials must never be stored in raw payloads, manifests, reports, or GUI output.

## Silver canonical facts

Silver is normalized, point-in-time football truth:

```text
competitions
seasons
teams
players
matches
lineups
match_events
odds_snapshots
market_catalog
market_aliases
settlement_rules
provider_identity_map
```

Silver should be partitioned by sport, competition, season, and snapshot date. It is the long-term source for factual replay and identity/market mapping.

## Gold training features

Gold is model-ready and leak-safe:

```text
gold_match_features
gold_team_snapshots
gold_player_snapshots
gold_market_features
gold_live_state_features
labels
settlements
paper_ledger
clv_reports
```

Gold must preserve prediction-time boundaries:

```text
feature.observed_at <= prediction_time
label.created_after final/settled state
```

Random train/test splits are forbidden. Walk-forward evaluation is required.

## Codec strategy

Keep:

```text
jsonl.gzip for small CI/runtime packs
```

Add:

```text
parquet.zstd for large history/training tables
json.zstd or jsonl.zstd for temporary raw payload snapshots
```

Parquet+Zstd is preferred for large tables because it supports column scans, partition pruning, compact numeric/categorical storage, and faster training reads.

## Rust migration

The migration begins with storage metadata and validation in `rust-core/src/storage_v2.rs`.

Next steps:

```text
1. Add JSONL.Zstd raw snapshot reader/writer.
2. Add Parquet.Zstd metadata contract and feature table writer.
3. Move provider cache manifests from Python into Rust.
4. Move silver canonical writers into Rust.
5. Move gold feature writers into Rust.
6. Build walk-forward dataset loader in Rust.
```

Python remains acceptable for notebooks, one-off exploration, and provider prototypes before their contracts stabilize.

## Acceptance

v233 is accepted when:

```text
current jsonl.gzip pack compatibility remains intact
storage v2 contract validates
Rust storage metadata structs compile and test
Python smoke validates current pack stats and v2 safety policy
CI stores no credential values and performs no provider calls
```
