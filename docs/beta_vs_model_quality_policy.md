# Beta Release vs Model Quality Policy

This project intentionally separates the desktop beta release path from the model-training and prediction-quality path.

## Core rule

```text
GUI beta can move fast.
Prediction/training engine must move slow.
```

A downloadable Windows/Linux beta may ship as a research GUI, local file adapter, report viewer, and pipeline preview. It must not claim strong prediction quality until the model pipeline proves it with real historical data, no-leak evaluation, calibration, and paper-only trust gates.

## What the early beta may do

The early desktop beta may include:

```text
Windows/Linux GUI
local files only
sample/report previews
historical file adapter page
historical materialization page
storage/report status pages
trust gates visible
training locked
no real betting recommendations
```

Acceptable positioning:

```text
research GUI beta
pipeline preview
local historical-data tooling
paper-only evaluator shell
```

Unacceptable positioning:

```text
profitable predictor
strong prediction engine
real betting advisor
validated betting model
ready-to-bet system
```

## Model/training gates

The prediction engine must remain locked until all critical quality gates are proven:

```text
no random train/test split
chronological or walk-forward evaluation only
no feature leakage
prediction timestamps before kickoff
settlement labels available after prediction time
fixtures, odds, settlements, and identities reproducible from local data
content hashes and storage manifests stable
baseline comparison required
calibration required
no-vig edge required
paper CLV required
sample size and confidence checks required
performance benchmark required
reproducibility benchmark required
```

## Trust states

Until the above gates are satisfied, reports and GUI panels must keep:

```text
ready_for_training = false
trust_status = sample_only or research_only
recommendation_output_present = false
credential_values_present = false
live_provider_calls_allowed = false
```

## Release path

The release path should focus on making the application easy to run:

```text
v471-v480 desktop beta release readiness
v481-v490 GitHub release artifacts / downloadable beta flow
v491-v500 beta QA checklist + offline demo dataset
```

The release path may improve packaging, installation, GUI flow, documentation, and offline demo usability without unlocking training.

## Quality path

After the GUI beta exists, the model-quality path should proceed slowly:

```text
real historical data scale-up
storage/performance benchmarks
no-leak walk-forward evaluation
baseline models
calibration and no-vig checks
paper CLV checks
only then serious training
```

## Decision rule

When there is tension between shipping faster and preserving model trust:

```text
ship GUI polish faster
ship model claims slower
never bypass trust gates
```

This rule exists so future contributors do not confuse a usable desktop beta with a validated prediction engine.
