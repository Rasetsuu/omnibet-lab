# v86b Curated League Universe

FootyStats is useful as a broad reference index because its leagues page exposes a huge global football catalogue, including popular competitions, country buckets, and continental/special competitions.

We should not import every league. The default universe is curated.

## Included by default

```text
high-signal tier-1 European domestic leagues
major UK depth
major Americas leagues
continental/special competitions
selected high-signal non-Europe leagues
```

## Excluded by default for now

```text
youth leagues
reserve leagues
low-signal lower divisions
duplicate regional cups
women competitions until a separate model path exists
```

This exclusion is not a quality judgement. It prevents mixing competitions with different distributions into the same model before the correct model paths exist.

## Scopes

```text
core_train       highest priority default model universe
expanded_train   trainable after source coverage exists
reference_only   useful for mapping/cross-checking, not default training yet
```

## Current target

The v86b smoke requires:

```text
at least 45 total entries
at least 30 trainable entries
at least 10 core train entries
Europe, UK, Americas, special, and non-Europe coverage
```

## FootyStats role

```text
reference/cross-check layer only
not a scraping target
no website automation in CI
manual/permitted snapshots only
```

## Next use

v87-v94 real historical adapters should target this universe first instead of trying to ingest every available competition.
