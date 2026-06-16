# v23 Multi-Source Data Adapters

v23 broadens the data layer beyond the existing core CSV and StatsBomb path.

## New adapters

```text
python_lab/adapters/openfootball_json_adapter.py
python_lab/adapters/wyscout_public_adapter.py
python_lab/multisource_lab.py
```

## Existing adapter reused

```text
python_lab/adapters/football_data_uk_adapter.py
```

## CI sample sources

```text
data/samples/openfootball_sample.json
data/samples/wyscout_public_sample_matches.json
data/samples/wyscout_public_sample_events.json
```

The CI smoke now combines:

- Football-Data style result/odds CSV
- OpenFootball-style fixture/result JSON
- Wyscout-style event JSON
- StatsBomb remains covered by the v20 scale pipeline

## Identity report

`multisource_lab.py` creates:

```text
entity_identity_candidates
```

The first version groups team names by normalized aliases and reports multi-source candidates. This is not final entity resolution, but it starts the contract for matching the same team/player across sources.

## Exported pack

CI exports:

```text
data_packs/football_multisource_v1
```

and verifies it with:

- Python pack verifier
- Rust pack verifier

## Why this matters

A real betting model needs source diversity:

- long match history
- event/player data
- lineups
- odds snapshots
- closing odds
- source-specific IDs
- identity mapping between all of them

v23 is the bridge from one-source experiments toward a larger multi-source historical lake.

## Honesty

The bundled OpenFootball/Wyscout files are tiny CI samples. They validate adapter contracts, not model quality. Bigger local backfills will use the same adapters and pack verification path.
