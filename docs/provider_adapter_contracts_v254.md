# v254 Offline Provider Adapter Contracts

v254 defines offline request/response contracts for the priority beta provider adapters.

## Scope

```text
odds provider snapshot fixture
football fixture/event provider fixture
adapter request contracts
adapter response shape contracts
adapter health report rows
desktop adapter surface contract
```

## Priority adapters

```text
odds_provider_snapshot_v1 -> the_odds_api
football_fixture_event_provider_v1 -> api_football
```

The live provider names remain mapped from v253, but v254 uses offline local fixtures only.

## Local fixtures

```text
data/provider_fixtures/v254/odds_provider_snapshot.sample.json
data/provider_fixtures/v254/football_fixture_event.sample.json
```

## CI safety

```text
paper_only: true
network_calls_allowed_in_ci: false
credentials_stored_in_repo: false
live_fetch_enabled: false
ci_fixture_only: true
```

## Health rows

The Rust validator emits one row per adapter:

```text
adapter_id
provider_id
fixture_loaded
contract_ok
normalization_targets
blockers
```

## Desktop surface

The desktop can show adapter contracts, fixture status, missing fields, and normalization targets.

Live fetch remains disabled until a later batch adds safe credential handling and live adapter smokes outside CI.

## Next beta-oriented batch

v255 should implement offline normalization preview rows from these provider fixtures:

```text
odds fixture -> normalized odds snapshot candidates
football fixture/event fixture -> normalized fixture/result/event candidates
provider identity links
adapter health summaries for market terminal display
```
