# v58-v61 Desktop Local Foundation

This milestone completes the next local-desktop foundation layer before the first release-candidate packaging work.

## v58 Tauri/Rust build preflight

The desktop package metadata is bumped to:

```text
0.5.0
```

and checked across:

```text
tauri-app/src-tauri/tauri.conf.json
tauri-app/src-tauri/Cargo.toml
tauri-app/package.json
```

The preflight validates the static frontend shape, command registration, no web-server dependency, local path handling, and Windows/Linux Python selection.

## v59 persisted review decisions

Review decisions now have a local JSONL store contract:

```text
.omnibet-local/review_decisions/review_decisions.jsonl
```

The desktop bridge adds:

```rust
save_review_decision(review_type, review_id, decision, reason)
```

Allowed review types:

```text
unknown_market
provider_identity
```

Allowed decisions:

```text
accepted
rejected
needs_review
```

These are still local decisions. Promotion into production mapping tables remains a later milestone.

## v60 workflow run UX

Local workflow results now include richer status metadata:

```text
state
started_at_unix
finished_at_unix
report_path_hint
refresh_hint
stdout_preview
stderr_preview
```

The Settings page shows per-workflow status and expected report paths.

## v61 local data directory contract

The local desktop layout is standardized by:

```text
configs/local_data_contract.v61.json
```

Default root:

```text
.omnibet-local/
```

Directory contract:

```text
configs/
reports/
build/
exports/
review_decisions/
logs/
cache/
```

The root can be overridden with:

```text
OMNIBET_HOME
```

## Smoke

```bash
python python_lab/desktop_local_foundation_smoke.py \
  --root . \
  --platform-name local \
  --out reports/ci_v58_v61_desktop_local_foundation.json
```

The smoke validates:

```text
v58 package preflight
v59 decision store write/read/summary
v60 workflow UX fields
v61 local data directory materialization
Tauri command registration
PAPER_ONLY/no-network/no-key safety
```

## Safety

```text
Offline/local only.
No API keys.
No live provider calls.
No network provider calls in CI.
No shell execution.
No recommendation output.
```
