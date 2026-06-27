# v301-v310 Local Dataset Materialization Preview

This batched phase starts turning the post-v300 roadmap into generated local preview reports.

It does not call live providers, does not store credentials, does not write real Bronze/Silver/Gold tables, and does not train models. It creates the first local-only materialization preview that can later feed the Market Terminal from generated reports instead of only bundled samples.

## Included versions

```text
v301 local source manifest bundle UI/report
v302 fixture/result local import preview
v303 odds local import preview
v304 settlement label preview
v305 closing-odds/CLV preview
v306 Bronze-to-Silver candidate materialization preview
v307 Gold feature candidate preview
v308 coverage readiness desktop panel
v309 local-only dataset build smoke
v310 market-terminal data reload from generated local preview
```

## Local preview outputs

Generated reports:

```text
.omnibet-local/reports/local_v301_v310_dataset_materialization.json
.omnibet-local/reports/local_v301_v310_market_terminal_preview.json
```

Bundled desktop sample:

```text
tauri-app/src/dataset-materialization.sample.json
```

## Desktop panel

The Dataset Materialization page shows:

```text
source manifest bundle
fixture/result import preview
odds import preview
settlement label preview
closing-odds / CLV preview
Bronze/Silver/Gold candidate materialization preview
coverage readiness report
```

## Safety

```text
paper_only: true
local_first: true
live_provider_calls_allowed: false
credential_values_allowed: false
real_money_recommendations_allowed: false
writes_real_bronze_silver_gold: false
```

This phase emits preview reports only. Promotion into real storage remains blocked until later Rust writer phases.

## Market Terminal reload

v310 defines a generated local preview shape for the Market Terminal. It only allows:

```text
inspect
paper_watch_only
```

Forbidden actions remain:

```text
recommend_real_bet
place_bet
auto_stake
claim_profitability
```

## Files

```text
configs/local_dataset_materialization.v301_v310.json
data/materialization/v301_v310/local_dataset_materialization.sample.json
tauri-app/src/dataset-materialization.sample.json
tauri-app/src/dataset_materialization.js
python_lab/local_dataset_materialization_preview.py
python_lab/local_dataset_materialization_smoke.py
rust-core/src/local_materialization_v301.rs
.github/workflows/v301_v310_local_dataset_materialization.yml
```

## Acceptance

v301-v310 is accepted when:

```text
manifest bundle preview is defined
fixture/result import preview is defined
odds import preview is defined
settlement label preview is defined
closing-odds/CLV preview is defined
Bronze/Silver/Gold candidate previews are defined
coverage readiness panel is defined
generated report paths are defined
market terminal reload path is defined
desktop page and smoke are added
Rust module parses/validates the contract
no live calls, credentials, or recommendations exist
```
