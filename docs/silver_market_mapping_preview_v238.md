# v238 Silver Market Mapping Preview

v238 adds a preview layer between bronze market discovery and silver canonical facts.

It does not perform final silver promotion yet. It previews which provider market groups are safe to map and which must stay in review.

## Inputs

```text
bronze market discovery rows
v237 canonical market registry
```

## Output

```text
SilverMarketMappingPreview
  resolved_rows
  review_rows
  counts
  safety flags
```

## Offline sample result

From the saved The Odds API-style market sample:

```text
raw bronze market rows: 8
unique provider market groups: 7
resolved groups: 6
review groups: 1
blocked promotions: 1
```

The resolved groups are:

```text
h2h
spreads
totals
corners
shots_on_target
player_shots_on_target
```

The review-blocked group is:

```text
special_combo_unknown
```

## Safety

v238 keeps the same safety rules:

```text
preview only
unknown markets are not auto-promoted
review rows are not promoted
resolved rows require canonical market id
resolved rows require settlement rule
player market lineup gate is preserved
```

This means `special_combo_unknown` cannot become a silver market row until a human-approved registry alias and settlement rule exist.

## Rust module

```text
rust-core/src/silver_market.rs
```

Provides:

```text
SilverMarketMappingPreview
SilverMarketMappingRow
SilverMarketReviewRow
build_silver_market_mapping_preview
build_preview_from_offline_samples
```

## Next step

v239 should add silver fixture/team/player identity preview. Market mapping alone is not enough; provider fixture/team/player ids also need safe canonical identity resolution before live World Cup data can become training facts.
