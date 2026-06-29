# Roadmap after v521-v530 Paper Market Builder Preview

This document exists so the project direction does not get lost.

## Product target

The normal user GUI should become:

```text
open app
see incoming/live/local matches
select match
press one preview button
see paper market-builder style forecast
track result later
```

The normal GUI should not expose training controls, import controls, materialization internals, baseline reports, calibration reports, or storage/debug panels.

Those can exist behind Advanced mode for development, but not as the default user experience.

## Current GUI direction

Use the name:

```text
Paper Market Builder
```

Avoid naming the normal UI as a real betting slip or bet builder. The output must remain paper-only until the trust gates are real.

Visible preview sections should include:

```text
Paper lean
Confidence
Main lines
Double chance style preview
Goals preview
GG / BTTS preview
Team goals
Score-band candidates
Risk flags
```

Raw JSON should stay hidden inside a details/debug section.

## Training direction

Training should not be a normal GUI button.

The intended flow is:

```text
app detects local completed-match data
background pipeline validates timestamps and labels
background training/evaluation runs only when no-leak gates pass
GUI only shows model/data status
```

Unsettled/current matches are never training rows. They are only pre-kickoff paper-preview rows until settled.

## Data scale-up direction

The next serious engine work should collect and normalize historical football data from multiple legal/public or user-provided sources.

Priority data types:

```text
fixtures
results
closing odds
opening odds
team/player availability when available
competition strength
market movement
settlement labels
```

All provider/source adapters should stay local-first and cache-first. No secret values in repo. No automatic live calls in CI.

## Rust migration direction

Move stable logic into Rust when contracts are settled:

```text
fixture normalization
market normalization
feature building
settlement joins
walk-forward splits
calibration reports
prediction runtime
batch paper preview runner
```

Python can remain for experiments and smoke checks, but production-ish runtime should trend toward Rust.

## GUI polish later

Do not over-polish the GUI before the engine is useful.

Order:

```text
1. Make prediction preview explicit and understandable.
2. Build reliable training/evaluation pipeline.
3. Move stable runtime to Rust.
4. Improve GUI design and visual polish.
5. Add more user features.
```

## Immediate next phases

```text
v531-v540 local completed-match ingest for World Cup/results
v541-v560 no-leak training/evaluation scaffold
v561-v580 Rust batch paper preview runner
v581-v600 GUI model/data status and improved layout
```
