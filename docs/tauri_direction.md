# GUI Direction: Tauri over Qt

Project decision: use Tauri for the final desktop GUI.

## Reasoning

- The existing `web_gui/index.html` can evolve into the frontend instead of being thrown away.
- Rust commands can host stable inference/value-betting logic.
- Python can remain the research/training layer.
- Packaging can target Windows and Linux.

## Planned architecture

```text
Python lab
  trains/tests models
  exports stable params/artifacts
        ↓
Rust core
  reads SQLite/CSV/model params
  runs inference, odds, Kelly, bet-builder
        ↓
Tauri GUI
  dashboard, prediction cards, odds table, bet-builder tickets
```

## What stays Python

- heavy ML experiments
- data science notebooks/scripts
- model comparison and backtests

## What moves to Rust

- stable Poisson/Dixon-Coles inference
- odds format conversion
- overround removal
- EV/Kelly
- SQLite feature reads
- bet-builder scoring
