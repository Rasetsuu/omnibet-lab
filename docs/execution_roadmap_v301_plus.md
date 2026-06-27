# v301+ Execution Roadmap

This roadmap locks the next execution direction after the v291-v300 Market Terminal MVP.

The project has finished the contract and sample-MVP spine:

```text
v259 source generate-refresh
v260 source filters/details
v261 upcoming/live fixture source contract
v262-v265 odds + live panel + live snapshots + prediction context bundle
v266-v270 Storage V2 compression foundation
v271-v280 historical dataset foundation
v281-v290 baseline training and evaluation
v291-v300 market terminal MVP
```

The next work must move from planning-only contracts into generated local data, Rust writers, evaluation reports, and UI surfaces.

## Core direction

```text
UI: already started with v291-v300 and continues immediately.
Python to Rust: starts now, heavily from v311-v320.
Compression: chosen in v266-v270, implementation starts v311-v320.
Training on data: starts seriously after local dataset materialization and no-leak checks.
Prediction improvement: starts after no-vig baselines and walk-forward evaluation exist.
```

## Runtime split

Rust owns stable runtime paths:

```text
storage writers
manifest validation
source normalization
Bronze/Silver/Gold materialization
dataset loader
walk-forward evaluator
desktop command backend
market-terminal generated report loading
```

Python remains for research and fast iteration:

```text
notebooks
quick model experiments
feature experiments
prototype training
analysis scripts
smoke tests until Rust equivalents exist
```

Do not delete Python suddenly. Move stable, repeatable, GUI-facing logic into Rust phase by phase.

## Compression decision

Use the v266-v270 storage direction:

```text
Bronze raw provider snapshots:
  JSONL.Zstd / JSON.Zstd
  temporary, deletable after verified promotion

Silver canonical facts:
  Parquet.Zstd
  long-term

Gold training features:
  Parquet.Zstd
  long-term

Small CI/runtime packs:
  JSONL.GZ remains supported

Recent local runtime cache:
  SQLite or small JSONL.GZ
```

## Next batched phases

### v301-v310 — Real local dataset materialization preview

Goal: move from bundled samples to generated local preview reports.

```text
v301 local source manifest bundle UI/report
v302 fixture/result local import preview
v303 odds local import preview
v304 settlement label preview
v305 closing-odds/CLV preview
v306 Bronze-to-Silver candidate materialization preview
v307 Gold feature candidate preview
v308 coverage readiness desktop panel
v309 local-only dataset build smoke
v310 market-terminal data reload from generated local preview
```

Safety:

```text
no live provider calls
no credentials
no real training claim
no betting recommendation
```

### v311-v320 — Rust Storage V2 writers and compression implementation

Goal: start implementing the chosen storage/compression path in Rust.

```text
JSONL.Zstd raw snapshot writer
JSON.Zstd raw payload writer
Parquet.Zstd metadata/writer contract hooks
provider cache manifest writer
Bronze manifest verification
Silver table manifest writer
Gold feature manifest writer
row counts and content hashes
retention/delete-after-promotion gates
local storage smoke
```

This phase is where the Python-to-Rust migration becomes concrete for storage.

### v321-v330 — Rust dataset loader and walk-forward evaluator

Goal: make the no-leak dataset loading/evaluation path real enough to drive reports.

```text
walk-forward window loader
prediction_time boundary checks
feature_observed_at <= prediction_time checks
label_created_after_settlement checks
market-family split checks
no random split enforcement
report writer for evaluation windows
coverage/readiness gate integration
```

### v331-v340 — First actual baseline training reports

Goal: start real baseline training only after local Gold/settlement data exists.

```text
1X2 no-vig market baseline report
totals no-vig market baseline report
BTTS no-vig market baseline report
simple Poisson/Elo/team-strength candidate report
blocked/partial report when data is insufficient
model artifact manifest
```

Rule:

```text
If settlement labels, closing odds, or no-leak windows are missing, emit blocked reports instead of fake metrics.
```

### v341-v350 — Calibration, CLV, and no-vig comparison reports

Goal: decide whether any model deserves paper-watch trust.

```text
calibration ECE/MCE reports
reliability tables
Brier/log-loss reports
no-vig baseline deltas
paper CLV reports
closing-line value summary
model trust gate updates
```

No model may move beyond sample/experimental without these reports.

### v351-v360 — Market terminal loads generated predictions

Goal: connect generated local model/evaluation output to the desktop Market Terminal.

```text
market terminal generated report loader
prediction table reload from local reports
trust/blocker badges from generated reports
source freshness badges from local materialization
paper watchlist generated from local rows
paper ledger preview from local rows
```

### v361-v370 — Prediction improvement experiments

Goal: improve beyond market-implied baselines only after baselines are measurable.

```text
team-strength features
recent form features
home/away features
rest/travel if available
lineup-aware features
event/stat features where available
market movement features
calibrated candidate models
```

### v371-v380 — Live prediction loop, still paper-only

Goal: use live state safely without leakage.

```text
live snapshot refresh loop
match clock/state freshness
live odds freshness
lineup/event/stat freshness
live context bundles
live paper-watch snapshots
post-match settlement join after final only
```

### v381-v390 — Bilet builder correlation engine

Goal: prepare same-game paper ticket logic without unsafe independence assumptions.

```text
correlation tags
same-game conflict checks
market family compatibility
selection dependency warnings
paper-only ticket builder
stake disabled unless validated_paper gates pass
```

### v391-v400 — Beta polish and release candidate

Goal: polish the app into a usable local beta.

```text
Windows/Linux release checks
portable data directory checks
settings polish
source status polish
market terminal polish
paper ledger polish
error handling
local report export/import
release candidate smoke
```

## Training order

Prediction work must follow this order:

```text
1. market-implied no-vig baseline
2. simple 1X2 / totals / BTTS baselines
3. Poisson / Elo / team-strength candidates
4. calibrated candidates
5. feature-rich lineup/event/player models
6. live-state models
7. same-game correlation and bilet builder logic
```

## Trust rule

No model should be trusted unless it passes:

```text
walk-forward evaluation
no-vig baseline comparison
calibration report
paper CLV report
settlement coverage threshold
closing odds availability
model trust gate
```

No model should claim profitability from sample data.

## Immediate next step

Start with:

```text
v301-v310 real local dataset materialization preview
```

That phase bridges the Market Terminal MVP from bundled sample data to generated local reports the app can reload.
