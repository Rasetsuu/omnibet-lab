# v33 Canonical Resolver and Alias Mapping Engine

v33 adds the canonical resolver layer needed before real provider ingestion becomes safe.

The problem:

```text
same thing, different name
different thing, similar name
short player names
translated market names
provider-specific team names
```

False merges are dangerous. Missing data is safer than wrong data.

## Resolver philosophy

```text
RAW LAYER:
  keep exactly what the provider/bookmaker said

CANONICAL LAYER:
  OmniBet's audited belief about what it means
```

Never mutate or discard the raw provider value.

## New warehouse tables/views

```text
canonical_teams
team_aliases
canonical_players
player_aliases
canonical_markets
market_aliases
canonical_selections
selection_aliases
resolver_mapping_candidates
resolver_mapping_decisions
resolver_review_queue
```

## Matching strategy

The resolver uses layers:

```text
1. exact provider/source ID where available
2. exact alias match
3. normalized text match
4. fuzzy text match
5. context match
6. confidence score
7. auto-map only above safe threshold
8. otherwise keep in review queue
```

Context can include:

```text
team
country
competition
match date
shirt number
birth date
position
provider player ID
```

## Safety thresholds

Initial smoke policy:

```text
auto-map threshold: >= 0.95
review threshold: below auto threshold or missing canonical id
```

Future work can tune thresholds per entity type.

## Dangerous examples

These must remain separate:

```text
Shots != Shots on target
Player shots != Team shots
1X2 regulation != To qualify
Player to score != First goalscorer
Cards != Booking points
Total corners != Team corners
```

## CI smoke

```bash
cd python_lab
python canonical_resolver_smoke.py \
  --db ../build/omnibet_v33_resolver_smoke.sqlite \
  --out ../reports/ci_v33_canonical_resolver_smoke.json
```

The smoke proves:

```text
Man. Utd -> Manchester United
MAN UTD -> Manchester United
K. Mbappe -> Kylian Mbappé with France context
Mbappe -> Kylian Mbappé with France context
Cornere -> total corners
Lovituri de colț -> total corners
Shots and shots on target remain separate
Final and To qualify remain separate
unknown raw market goes to resolver_review_queue
```

## What v33 does not do

```text
No provider calls.
No API keys.
No website automation.
No model training on uncertain mappings.
No staking/profit claim.
```

v33 only builds the resolver storage and deterministic smoke.
