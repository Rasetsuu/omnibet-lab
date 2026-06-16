# v42-v48 Platform Hardening Pack

This combined milestone moves OmniBet from an offline end-to-end skeleton toward a safer research platform foundation.

## v42 Provider identity hardening

Adds provider identity candidate/review storage for:

```text
events
teams
players
```

It proves deterministic offline matching across the The Odds API-style sample and API-Football-style sample, while keeping ambiguous examples in a review queue.

Smoke:

```bash
cd python_lab
python provider_identity_hardening_smoke.py \
  --db ../build/omnibet_v42_identity_hardening.sqlite \
  --out ../reports/ci_v42_identity_hardening.json
```

## v43 Shared schema promotion

Adds `python_lab/provider_pipeline_schema.py`, a shared schema helper for provider timeline, settlement, feature, identity, player truth, export, model-report, and live-scaffold tables.

Smoke:

```bash
cd python_lab
python schema_promotion_smoke.py \
  --db ../build/omnibet_v43_schema_promotion.sqlite \
  --out ../reports/ci_v43_schema_promotion.json
```

## v44 Expanded settlement coverage

Adds deterministic rule coverage for additional football market families:

```text
both teams to score
double chance
draw no bet
team total goals
yellow/red cards
first half 1X2
```

It explicitly refuses to settle qualification-style markets without qualification truth.

Smoke:

```bash
cd python_lab
python expanded_settlement_smoke.py \
  --db ../build/omnibet_v44_expanded_settlement.sqlite \
  --out ../reports/ci_v44_expanded_settlement.json
```

## v45 Player prop truth skeleton

Adds player-level truth storage and settles the existing Kylian Mbappe player shots-on-target sample rows.

Missing player truth remains unsupported.

Smoke:

```bash
cd python_lab
python player_prop_truth_smoke.py \
  --db ../build/omnibet_v45_player_prop_truth.sqlite \
  --out ../reports/ci_v45_player_prop_truth.json
```

## v46 Feature export pack

Exports feature snapshots and settlement labels into compressed files:

```text
event_feature_snapshots.jsonl.gz
market_feature_snapshots.jsonl.gz
settlement_labels.jsonl.gz
manifest.json
```

Smoke:

```bash
cd python_lab
python feature_export_pack_smoke.py \
  --db ../build/omnibet_v46_feature_export.sqlite \
  --out-dir ../build/v46_feature_export_pack \
  --out ../reports/ci_v46_feature_export_pack.json
```

## v47 First model pass

Runs a tiny offline structural model smoke over leak-guarded feature rows.

It writes metrics and a caveat that this is a toy offline smoke, not a predictive quality claim.

Smoke:

```bash
cd python_lab
python first_model_pass_smoke.py \
  --db ../build/omnibet_v47_first_model_pass.sqlite \
  --out ../reports/ci_v47_first_model_pass.json
```

## v48 Env-gated live provider scaffold

Registers future live provider entrypoints while proving CI is disabled by default:

```text
The Odds API scaffold
API-Football scaffold
```

No network call is performed in CI.

Smoke:

```bash
cd python_lab
python live_provider_scaffold_smoke.py \
  --db ../build/omnibet_v48_live_provider_scaffold.sqlite \
  --out ../reports/ci_v48_live_provider_scaffold.json
```

## Safety

```text
Offline samples only in CI.
No API keys in repo.
No live provider calls in CI.
No website automation.
No recommendation output.
No model-quality claim.
Unsupported rows stay unsupported.
Ambiguous identity rows go to review.
```
