# v55-v56 Desktop Settings and Local Run Controls

This milestone adds the next desktop-first GUI layer after the review pages.

## v55 Settings page

The Settings page now renders:

```text
local paths
runtime mode
provider status
safety flags
```

Provider rows show only:

```text
provider id
enabled flag
env var name
key status label
```

API key values are never displayed.

## v56 Local run buttons

Settings also renders local workflow buttons from settings data.

Initial allowlisted workflow ids:

```text
generate_dashboard_report
generate_review_report
run_leak_guard
run_feature_export
run_settlement_truth
run_first_model_pass
```

The Rust/Tauri backend adds:

```rust
load_app_settings(path_hint: Option<String>)
run_local_workflow(workflow_id: String)
```

`run_local_workflow` uses a fixed allowlist and `Command::new(...)` directly. It does not execute shell strings.

## Cross-platform note

Python invocation uses:

```text
OMNIBET_PYTHON if set
python on Windows
python3 elsewhere
```

This keeps the workflow bridge compatible with Windows and Linux desktop paths.

## Smoke

```bash
python python_lab/settings_runs_smoke.py \
  --root . \
  --out reports/ci_v55_v56_settings_runs.json
```

The smoke validates:

```text
settings files exist
sample settings are parseable
settings page markers exist
local workflow buttons exist
Tauri settings command is registered
Tauri workflow command is registered
workflow ids are allowlisted
no shell execution markers exist
PAPER_ONLY marker remains present
```

## Safety

```text
Offline/local commands only.
No shell execution.
No API key values in UI.
No live provider calls.
No network in CI.
No recommendation output.
```
