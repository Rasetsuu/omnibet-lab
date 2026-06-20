# v234 Rust Provider Runtime Foundation

v234 starts moving provider/source ingestion from Python planning into typed Rust runtime contracts.

This does **not** add live HTTP fetching yet. It defines the safe foundation needed before live adapters are implemented.

## Providers

Initial provider definitions:

```text
The Odds API      odds snapshots, market discovery, historical odds
API-Football      fixtures, live state, lineups, events, statistics, players
Sportmonks        secondary fixtures, livescores, events, lineups, players, odds
Betfair Exchange  exchange market reference and historical backtest
```

All providers are disabled by default.

## Network policy

```text
CI live calls: false
providers enabled by default: false
manual enable required: true
credential values stored: false
credential values displayed: false
```

The runtime may show only credential status:

```text
present
missing
```

It must never display or persist the credential value.

## Snapshot contract

Every provider snapshot must include:

```text
source_id
request_kind
captured_at
observed_at
payload_sha256
payload_codec
payload_path
```

This is the bridge into the v233 storage model:

```text
provider payload -> source snapshot manifest -> bronze raw snapshot -> silver canonical facts -> gold training features
```

## Adapter stages

Provider implementation should advance through these stages:

```text
contract_only
offline_sample_parser
manual_live_fetcher
scheduled_capture
canonical_promotion
training_dataset_promotion
```

CI should stay at `contract_only` / `offline_sample_parser` and never require secrets or provider availability.

## Canonical outputs

The provider runtime should eventually normalize payloads into:

```text
provider_status
fixture_snapshot
live_state_snapshot
odds_snapshot
market_discovery_snapshot
lineup_snapshot
event_snapshot
player_snapshot
```

These outputs feed identity mapping, market mapping, settlement, features, and model training.

## Rust module

The first Rust provider runtime module is:

```text
rust-core/src/provider.rs
```

It defines:

```text
ProviderRuntimeContract
ProviderDefinition
ProviderStatus
ProviderCapabilities
CredentialStatus
SourceSnapshotManifest
```

It also validates the provider contract and creates offline sample snapshot manifests with SHA-256 hashes.

## Acceptance

v234 is accepted when:

```text
provider contract parses and validates in Rust
provider status never exposes credential values
sample snapshot manifests hash payload content
providers remain disabled by default
CI performs no live provider calls
Python provider runtime smoke passes
Rust provider tests pass
```
