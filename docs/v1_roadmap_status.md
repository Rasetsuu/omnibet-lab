# OmniBet Lab v1.0 Roadmap Status

This document defines what "v1.0" means for OmniBet Lab.

## Honest current status

OmniBet is not trained well yet.

Current state:

```text
Desktop GUI beta: done enough for testing
Paper market catalog: working
GUI data pipeline status: working
Local result ingest: started
Eval gate: present
Source catalog: present
Local adapter samples: present
Rust row normalizer: present
Rust local parsers: present
Rust sample runner: wired in CI
Large historical data: not done
Useful trained model: not done
Calibrated confidence: not done
Player/corner/card models: not done
```

## Rough progress

For a paper-only v1.0 desktop research app:

```text
Current progress: about 40 percent
```

For a serious sportsbook-grade predictor:

```text
Current progress: less than 10 percent
```

The first v1.0 target is the paper-only research app, not a real-money advice product.

## v1.0 definition

v1.0 should mean:

```text
1. Normal desktop app opens cleanly on Linux and Windows.
2. User can select fixtures from a local/upcoming fixture pack.
3. Paper market catalog is readable and honest.
4. Data status explains what is available and what is locked.
5. Historical completed rows can be imported from local files.
6. The train/eval gate blocks unsafe or too-small data.
7. A simple baseline model can be trained only after enough rows exist.
8. Evaluation report is shown before any confidence is trusted.
9. Predictions are clearly paper-only.
10. Release artifacts are reproducible through CI.
```

## What is not v1.0

v1.0 does not mean:

```text
profitable prediction engine
real betting advice
staking output
live sportsbook integration
full player prop coverage
corners/cards/free-kicks model parity
```

Those belong after v1.0.

## Remaining phases to v1.0

### Phase A: Larger historical row packs

Goal:

```text
Move from local samples to enough completed rows for basic evaluation.
```

Needed:

```text
football-data shaped local packs
openfootball shaped local packs
source metadata
season/team normalization
row-count reports
```

### Phase B: Feature builder v1

Goal:

```text
Build simple timestamp-safe features from completed rows.
```

Needed:

```text
team rolling form
goals for/against rolling windows
home/away splits
rest days when available
simple strength prior slot
```

### Phase C: Baseline model v1

Goal:

```text
Train a simple baseline only after the gate passes.
```

Needed:

```text
1X2 baseline
basic goals baseline
walk-forward split
calibration report
holdout metrics
```

### Phase D: GUI evaluation report

Goal:

```text
Show model status honestly in the desktop app.
```

Needed:

```text
row count
last evaluation date
metrics
confidence status
locked market families
```

### Phase E: v1.0 release polish

Goal:

```text
Package a stable paper-only desktop beta as v1.0.
```

Needed:

```text
Linux/Windows release artifacts
README quickstart
known limitations
sample data instructions
no secrets/no network CI proof
```

## First v1.0 finish line

The first meaningful v1.0 is achieved when:

```text
A user can open the desktop app, load local completed-data packs, run/inspect a gated baseline evaluation, then preview paper-only fixture outputs with honest confidence status.
```

## After v1.0

After v1.0, improve toward:

```text
larger datasets
better feature families
more competitions
calibration improvement
corners/cards event adapters
lineups/player event adapters
faster Rust runtime
better GUI reports
```
