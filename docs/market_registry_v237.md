# v237 Canonical Market Registry

v237 adds the first canonical market registry and provider alias resolver.

This is required before bronze provider rows can safely become silver canonical facts.

## Why

Provider markets are not safe to promote by name alone. The same bookmaker/provider key can imply different settlement rules, periods, line scopes, or player scopes depending on sport, market, and endpoint.

OmniBet must never silently guess unknown markets.

## Canonical markets in v237

```text
match_result_1x2
handicap
total_goals
total_corners
team_shots_on_target
player_shots_on_target
```

Each canonical market has:

```text
family
display name
period
selection scope
line-required flag
player-required flag
lineup-required flag
settlement rule
correlation group
```

## Provider aliases

The first aliases map The Odds API sample keys:

```text
h2h                    -> match_result_1x2
spreads                -> handicap
totals                 -> total_goals
corners                -> total_corners
shots_on_target        -> team_shots_on_target
player_shots_on_target -> player_shots_on_target
```

## Unknown markets

The sample market `special_combo_unknown` remains intentionally unmapped.

It must resolve to:

```text
status: needs_review
reason: unmapped_provider_market
promotion_allowed: false
```

Unknown provider markets cannot be auto-promoted into silver facts.

## Player market guard

Player prop markets require player context and usually confirmed/probable lineup context.

In v237:

```text
player_shots_on_target.player_required = true
player_shots_on_target.lineup_required = true
```

This protects future scorer/player-prop modeling from pretending it has enough information before lineup/expected-minutes data exists.

## Rust module

```text
rust-core/src/market_registry.rs
```

Provides:

```text
MarketRegistryContract
CanonicalMarket
ProviderMarketAlias
MarketResolution
resolve_provider_market
resolve_market_discovery_rows
promotion_allowed
```

## Acceptance

v237 is accepted when:

```text
known sample provider markets resolve
unknown sample provider market needs review
player prop market is lineup-gated
line markets require line scope
settlement rules are required
bronze market discovery rows can be checked
Python smoke passes
Rust tests pass
```

## Next step

v238 should promote safe bronze market discovery rows into a silver market mapping preview/report, while preserving unknown-market review rows for manual mapping.
