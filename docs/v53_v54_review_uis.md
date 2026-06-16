# v53-v54 Review UIs

This milestone adds the first desktop review pages after the v50-v52 GUI shell.

## v53 Unknown Market Review UI

The Unknown Queue page now supports a local review view for unmapped/unknown market rows.

Each row shows:

```text
provider
source/bookmaker
raw market name
raw selection
candidate mapping
confidence
local decision
reason
```

Local UI actions:

```text
Accept
Reject
Needs review
```

These actions update browser/Tauri UI state only. They do not persist production mappings yet.

## v54 Provider Identity Review UI

Adds an Identity Review page for provider entity matching.

It shows review rows for ambiguous cases such as:

```text
France U21 -> canonical_team:france
```

The row remains review-only because youth/senior national teams must not be auto-merged.

It also shows a candidate preview for auto-matched teams/players/events.

## Tauri command

The Rust backend adds:

```rust
load_review_report(path_hint: Option<String>)
```

It reads local JSON from allowlisted paths:

```text
build/v53_v54_review_data.json
reports/ci_v53_v54_review_ui.json
tauri-app/src/review-data.sample.json
```

No network calls are used.

## Smoke

```bash
python python_lab/review_ui_smoke.py \
  --root . \
  --review-out build/v53_v54_review_data.json \
  --out reports/ci_v53_v54_review_ui.json
```

The smoke checks:

```text
unknown market review rows exist
identity review rows exist
identity candidates exist
sample review JSON exists
review UI markers exist
review.js is linked
Tauri review command is registered
allowlisted review paths exist in Rust
PAPER_ONLY marker remains present
```

## Safety

```text
Offline/local files only.
No API keys.
No live provider calls.
No network in CI.
No recommendation output.
No persistence of review decisions yet.
```
