# v32 Raw Market Snapshot Warehouse

v32 turns v31's market discovery contract into actual SQLite warehouse tables.

The rule is:

```text
Hardcode stable contracts only.
Keep provider/bookmaker market data dynamic.
```

## Hardcoded on purpose

These are stable enough to hardcode:

```text
table names
required schema fields
known market-family IDs
settlement-scope enums
safety rules
```

## Not hardcoded

These must remain dynamic and provider-discovered:

```text
raw market names
raw selection names
provider market keys
bookmaker event IDs
lines
player names
team names
period labels
unknown market labels
```

## New warehouse objects

```text
raw_market_snapshots
market_mapping_rules
unknown_market_queue
```

### raw_market_snapshots

Append-only table for observed bookmaker/provider markets.

Important fields:

```text
observed_at
provider_id
bookmaker
provider_event_id
match_id
raw_market_key
raw_market_name
raw_selection_key
raw_selection_name
decimal_odds
line_raw
line_value
team_name_raw
team_id
player_name_raw
player_id
period_raw
settlement_scope_guess
mapped_market_id
mapping_confidence
needs_mapping
suspended
last_update
payload_sha256
raw_json
```

### market_mapping_rules

Stores mapping rules from provider raw names/keys into OmniBet market IDs.

Rules can be provider-specific or bookmaker-specific.

### unknown_market_queue

SQLite view grouping raw markets where:

```text
needs_mapping = 1
or mapped_market_id is null/empty
```

This makes unknown markets reviewable instead of discarded.

## CI smoke

```bash
cd python_lab
python market_snapshot_smoke.py \
  --db ../build/omnibet_v32_market_smoke.sqlite \
  --out ../reports/ci_v32_market_snapshot_smoke.json
```

The smoke inserts:

```text
mapped 1X2 sample
mapped total-goals sample
unmapped Superbet-style same-game combo sample
```

Then it proves:

```text
raw_market_snapshots has rows
unknown_market_queue has rows
mapped markets are counted
no provider calls were made
no scraping was performed
```

## Relationship to v31

v31 defined the market-discovery contract.

v32 stores it.

Future work should add real provider adapters only after this storage layer is stable.

## What v32 does not do

```text
No API keys.
No provider requests.
No website scraping.
No sportsbook account automation.
No staking or profit claim.
```
