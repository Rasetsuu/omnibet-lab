# v291-v300 Market Terminal MVP

This batched phase creates the first desktop-facing market terminal MVP surface.

It is still paper-only and sample-first. It does not place bets, does not recommend real-money actions, and does not enable the bilet builder. It gives OmniBet a usable terminal shape around fixtures, market rows, trust blockers, freshness, movement preview, and paper-only watchlist/ledger previews.

## Included versions

```text
v291 market terminal data contract
v292 fixture/market selection state
v293 prediction table renderer
v294 trust/blocker display
v295 paper-only watchlist action
v296 market movement preview
v297 paper ledger preview
v298 source freshness badges
v299 disabled bilet-builder placeholder
v300 desktop market terminal MVP smoke
```

## v291 - Market terminal data contract

The MVP data contract defines:

```text
fixtures[]
prediction_rows[]
paper_watchlist[]
paper_ledger_preview[]
bilet_builder_placeholder
```

The terminal consumes sample data only in this phase.

## v292 - Fixture and market selection state

The terminal shows selectable fixture rows with:

```text
canonical_fixture_id
label
competition
status
kickoff_time
source_freshness
available_markets
trust_summary
```

Selecting a fixture filters the prediction table locally.

## v293 - Prediction table renderer

Prediction rows include:

```text
canonical_fixture_id
market_key
selection_key
model_probability
fair_odds_decimal
bookmaker_odds_decimal
no_vig_probability
edge_vs_no_vig
trust_status
blockers
allowed_action
movement_preview
```

Null model probabilities are expected until models are validated.

## v294 - Trust and blocker display

Every row must expose trust status and blockers. Trust states remain:

```text
unsupported
sample_only
low_data
experimental
paper_watch
validated_paper
```

## v295 - Paper watchlist action

Allowed terminal actions are limited to:

```text
inspect
paper_watch_only
```

The sample watchlist is not a real betting slip.

## v296 - Market movement preview

Market rows can show opening/current/closing price preview fields. Missing closing prices stay explicit and block CLV claims.

## v297 - Paper ledger preview

The paper ledger preview forbids real stake:

```text
real_stake_allowed: false
```

## v298 - Source freshness badges

Freshness badges include:

```text
fresh_sample
stale_sample
missing_timestamp
offline_sample
```

## v299 - Disabled bilet builder placeholder

The bilet builder stays disabled until trust reaches:

```text
validated_paper
```

Default disabled reason:

```text
model_not_validated_for_bilet_builder
```

## v300 - Desktop smoke

The v300 smoke validates:

```text
contract fields
sample fields
HTML panel wiring
JS renderer binding
paper-only safety
forbidden real-money actions
Rust validation module
README/docs/workflow references
```

## Files

```text
configs/market_terminal_mvp.v291_v300.json
tauri-app/src/market-terminal.sample.json
tauri-app/src/market_terminal.js
docs/market_terminal_mvp_v291_v300.md
rust-core/src/market_terminal_v291.rs
python_lab/market_terminal_mvp_smoke.py
.github/workflows/v291_v300_market_terminal_mvp.yml
```

## Acceptance

v291-v300 is accepted when:

```text
market terminal data contract is defined
fixture/market selection state is defined
prediction table renderer is wired
trust/blocker display is required
paper watchlist action is safe
market movement preview is read-only
paper ledger preview forbids real stake
source freshness badges are required
bilet builder placeholder is disabled
Rust module parses/validates the contract
Python smoke validates contract/sample/docs/desktop/workflow
```
