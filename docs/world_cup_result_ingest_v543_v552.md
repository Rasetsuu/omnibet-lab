# v543-v552 World Cup Result Ingest

This phase starts the engine path after the GUI catalog work.

## Goal

Before training, OmniBet needs completed, timestamp-safe result rows.

The normal GUI can show previews for upcoming matches, but training/evaluation candidates must come only from settled matches.

## Added local result pack

```text
data/world_cup/v543_v552/world_cup_results.local.json
```

Initial rows:

```text
Brazil 2-1 Japan      settled -> candidate preview
Germany vs Paraguay   pending -> blocked
Netherlands vs Morocco pending -> blocked
```

## Candidate rule

A row can become a candidate only when:

```text
status = settled
home_score exists
away_score exists
label_available_after_utc exists
label_available_after_utc > kickoff_utc
```

Pending/current matches are never training rows.

## Output

The smoke writes:

```text
reports/ci_v543_v552_world_cup_result_ingest.json
reports/world_cup_training_candidates_v543_v552.json
```

The candidate preview is still not training. It is a safe bridge toward the next phase.

## Next

```text
v553-v570 no-leak training/evaluation scaffold
```

That phase should add a real model-training gate, but still keep training hidden from the normal GUI.
