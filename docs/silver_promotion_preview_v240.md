# v240 Silver Promotion Preview

v240 combines the market mapping preview and identity mapping preview before any provider rows can become silver facts.

It is still preview-only. It does not create training data and does not perform final silver promotion.

## Inputs

```text
v238 silver market mapping preview
v239 identity mapping preview
```

## Offline sample result

The saved samples currently produce:

```text
market review count: 1
identity review count: 0
blocked count: 1
silver ready: false
```

Why blocked:

```text
special_combo_unknown
```

The fixture/team/player identities are resolved, but that is not enough. A single unresolved market blocks the combined silver-ready bundle.

## Safety policy

```text
preview only
market mapping must be fully resolved
identity mapping must be fully resolved
blocked rows prevent silver-ready status
review rows are not promoted
training dataset promotion is forbidden
```

## Rust module

```text
rust-core/src/silver_promote_v240.rs
```

Provides:

```text
SilverPromotionPreview
SilverFactBundlePreview
SilverBlockedBundle
build_silver_promotion_preview
build_silver_promotion_preview_from_offline_samples
```

## Why this matters

This is the first combined gate that says:

```text
safe market mapping + safe identity mapping -> silver preview ready
```

or:

```text
any unresolved market/entity -> blocked review bundle
```

For the current sample, the correct result is blocked because `special_combo_unknown` still needs manual market registry review.

## Next step

v241 should add a review-queue artifact that combines unresolved market rows and unresolved identity rows into one human-review report. After that, a human-approved alias/settlement rule can unblock the sample market in a controlled way.
