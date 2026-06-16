# v39-v41 Feature Snapshots, Leak Guard, and Offline Paper Evaluation

This combined milestone moves the offline provider pipeline from storage/settlement into model-ready data safety.

## v39 Feature Snapshot Builder

Builds stable feature tables from the v37/v38 offline pipeline:

```text
event_feature_snapshots
market_feature_snapshots
```

Important separation:

```text
pre_event_market:
  decimal odds, implied probability, line, market id, selection
  no final score
  no settlement result
  model_eligible can be true

post_event_evaluation:
  settlement result/status allowed
  final_truth_allowed true
  model_eligible false
```

Smoke:

```bash
cd python_lab
python feature_snapshot_smoke.py \
  --db ../build/omnibet_v39_feature_snapshots.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v39_feature_snapshots.json
```

## v40 No-Future-Leak Guard

Checks that model-eligible rows do not contain future-only fields.

Rules checked:

```text
pre-event market rows contain no final score
pre-event market rows contain no settlement result/status
model_eligible rows have final_truth_allowed = false
post-event evaluation rows are not model eligible
pre-event cutoff time does not exceed commence time
event observation rows do not contain final truth
```

Smoke:

```bash
cd python_lab
python leak_guard_smoke.py \
  --db ../build/omnibet_v40_leak_guard.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v40_leak_guard.json
```

## v41 Offline Paper Evaluation

Evaluates only post-event rows that are already:

```text
mapped
settled
supported
```

It skips:

```text
unmapped markets
unsupported player props without player-level truth
unknown/special combo markets
```

Outputs include:

```text
evaluated row count
skipped rows and reasons
win/loss/push counts
mapped market counts
paper unit result
```

This is a structural accounting smoke, not a model-quality claim.

Smoke:

```bash
cd python_lab
python offline_paper_eval_smoke.py \
  --db ../build/omnibet_v41_offline_paper_eval.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v41_offline_paper_eval.json
```

## Safety

```text
Offline samples only.
No API keys.
No live provider calls.
No website automation.
No model-quality claim.
No recommendation output.
Unmapped/unsupported rows are not evaluated as valid markets.
```
