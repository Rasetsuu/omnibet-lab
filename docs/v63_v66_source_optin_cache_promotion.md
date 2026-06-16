# v63-v66 Source Opt-In, Local Cache, and Review Promotion

This milestone starts Phase 1 after the desktop RC.

## v63 source status and opt-in controls

The Settings page now exposes source controls with status-only credential metadata:

```text
source id
enabled flag
credential env name
credential status only
manual action flag
```

Source controls are disabled by default and manual-only.

No credential value is displayed or stored.

## v64 manual source cache actions

The Settings page has per-source cache buttons.

The action is manual and writes local source-shaped sample snapshots. CI uses offline samples only.

## v65 cached source snapshots

Cached snapshots are stored under the local data root:

```text
.omnibet-local/cache/source_snapshots/
```

Each source gets:

```text
snapshot_manifest.json
<kind>.sample.json
```

The cache index is:

```text
.omnibet-local/cache/source_snapshots/cache_index.json
```

## v66 review-decision promotion

Accepted local review decisions can be promoted into candidate-only mapping files:

```text
.omnibet-local/exports/mapping_rule_candidates.v66.json
```

Important: this does not mutate production mappings yet.

The output is candidate-only and contains:

```text
candidate kind
review id
candidate status
source decision
reason
```

## Helper

```bash
python python_lab/source_phase1.py --status
python python_lab/source_phase1.py --cache-samples --root .omnibet-local
python python_lab/source_phase1.py --promote --root .omnibet-local
```

## Smoke

```bash
python python_lab/source_phase1_smoke.py \
  --root . \
  --out reports/ci_v63_v66_source_phase1.json
```

The smoke validates:

```text
status-only credential metadata
sources disabled by default
manual-only controls
cached source-shaped snapshots
candidate-only promotion from accepted review decisions
UI controls
Tauri command registration
no shell execution
```

## Safety

```text
Offline/local CI only.
No credential values in UI/output/artifacts.
Sources disabled by default.
Manual actions only.
No background fetches.
No external source calls in CI.
No recommendation output.
```
