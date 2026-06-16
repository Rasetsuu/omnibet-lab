# v34 Safe Market Alias Apply Engine

v34 applies the v33 resolver to v32 raw market snapshots.

It is deliberately conservative:

```text
exact high-confidence aliases only
no fuzzy market auto-mapping yet
unknowns stay unknown
raw snapshots stay preserved
```

## Why this milestone matters

v32 created storage:

```text
raw_market_snapshots
unknown_market_queue
```

v33 created canonical aliases:

```text
canonical_markets
market_aliases
resolver_mapping_candidates
resolver_mapping_decisions
```

v34 connects them.

## What gets mapped

The smoke maps examples like:

```text
Cornere -> football_corners_total_regulation
Lovituri de colț -> football_corners_total_regulation
Shots -> football_shots_total_regulation
Shots on target -> football_shots_on_target_total_regulation
Final -> football_1x2_regulation
To qualify -> football_to_qualify
```

## What stays unknown

A raw provider market that has no exact high-confidence alias remains:

```text
needs_mapping = true
mapped_market_id = null
```

and stays visible in:

```text
unknown_market_queue
```

## Safety rules

```text
Do not fuzzy auto-map bookmaker markets yet.
Do not collapse dangerous near-matches.
Do not delete raw snapshots.
Do not use uncertain mappings for model features.
```

Dangerous separations remain enforced by the smoke:

```text
Shots != Shots on target
Final / 1X2 regulation != To qualify
```

## CI smoke

```bash
cd python_lab
python market_alias_apply_smoke.py \
  --db ../build/omnibet_v34_market_alias_apply.sqlite \
  --out ../reports/ci_v34_market_alias_apply.json
```

The report includes:

```text
counts_before
counts_after
apply_result
mapped_rows
unknown_market_queue
acceptance
```

## What v34 does not do

```text
No API keys.
No provider requests.
No website automation.
No live ingestion.
No model-quality claim.
```

v34 is the first safe bridge from raw provider markets to canonical OmniBet markets.
