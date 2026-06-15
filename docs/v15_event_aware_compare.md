# v15 Event-Aware Comparison

v15 adds a small comparison report over the public StatsBomb sample introduced in v14.

## New script

```text
python_lab/event_aware_compare.py
```

## What it compares

The script reads `gold_match_features` and compares two transparent heuristics:

1. **match-only**
   - goals for/against rolling differences
   - points/form differences
   - rest-day difference

2. **event-aware**
   - match-only fields
   - xG for/against rolling differences
   - shots for/against rolling differences
   - cards differences

## CI contract

The CI harness now downloads a larger public sample and requires at least one event-history row where prior event features exist.

It writes:

```text
reports/ci_event_aware_compare.json
```

and includes the compact result in:

```text
reports/ci_summary.json
```

## Important warning

This is not a claim that the event-aware heuristic is better. The sample is intentionally tiny and CI-friendly. v15 proves the evaluation plumbing:

```text
real public event data
  -> rolling event features
  -> event-aware comparison report
  -> CI-gated summary
```

The next step is a real trained/calibrated model over more data.
