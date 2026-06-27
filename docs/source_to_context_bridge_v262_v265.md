# v262-v265 Source-to-Context Bridge

This batched phase connects the v261 upcoming/live fixture source contract to the future market terminal.

It does not train a model, does not enable live provider calls in CI, and does not produce betting recommendations. It defines the offline-safe bridge shape that later Rust storage, training, and GUI work can consume.

## Included versions

```text
v262 odds snapshot source contract
v263 desktop upcoming/live matches sample panel
v264 live snapshot storage and retention contract
v265 prediction-ready match context bundle
```

## v262 - Odds snapshot source contract

v262 defines bookmaker/market odds rows that can join to v261 fixture/live rows.

Required row fields:

```text
provider
provider_event_id
provider_fixture_id
canonical_fixture_id
bookmaker
market_key
selection_key
price_decimal
is_in_play
market_status
last_update
observed_at
captured_at
freshness_status
missing_reason
```

Important rules:

```text
observed_at <= captured_at
missing odds are explicit rows or explicit missing reasons
unknown markets stay review/quarantine candidates
player props can remain missing until lineup/player/market mapping exists
```

## v263 - Desktop sample panel

v263 adds a sample-only desktop bridge panel. The panel shows:

```text
live/upcoming matches
odds preview rows
prediction context preview rows
selected match source details
trust blockers
```

This is still a source/context panel, not the final prediction terminal.

## v264 - Live snapshot storage and retention contract

v264 defines the snapshot lifecycle needed for games that are live or later settled.

Snapshot types:

```text
pre_match
live
post_match_settlement
```

Retention tiers:

```text
raw_bronze_temporary
silver_fact_long_term
gold_feature_long_term
```

Policy:

```text
raw provider payloads may be deleted after verified promotion
Silver facts and Gold features are kept long-term
settlement labels are stored separately from pre/live prediction features
```

## v265 - Prediction-ready match context bundle

v265 defines the object a future model or market terminal can safely consume.

Required context fields:

```text
context_id
provider_fixture_id
canonical_fixture_id
prediction_time
fixture_context
live_state_context
odds_context
market_availability_context
data_freshness_context
trust_blockers
prediction_readiness
allowed_actions
```

Allowed actions remain limited to:

```text
inspect_context
paper_watch_only
```

until later validation proves a market/model can be used in a paper ledger.

## No-leak boundary

Every source row and snapshot must preserve:

```text
observed_at <= captured_at <= prediction_time when used for prediction
```

Post-match settlement rows are allowed only after final/settled state and must not be mixed into pre-match/live features.

## Files

```text
configs/source_to_context_bridge.v262_v265.json
data/provider_fixtures/v262_v265/source_to_context_bridge.sample.json
tauri-app/src/live-source.sample.json
tauri-app/src/live_source.js
python_lab/source_to_context_bridge_smoke.py
.github/workflows/v262_v265_source_to_context_bridge.yml
```

## Acceptance

The bridge is accepted when:

```text
odds rows join to fixture rows
live/upcoming panel is wired and sample-only
snapshot rows define retention/deletion policy
post-match settlement is separate from prediction features
context bundles contain fixture/live/odds/market/freshness/trust fields
no secret values are present
no CI live calls are present
README/docs/workflow/smoke are updated
```
