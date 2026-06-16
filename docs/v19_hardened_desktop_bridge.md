# v19 Hardened Desktop Bridge

v18 added safe Tauri UI stubs. v19 replaces those stubs with a hardened bridge that calls the existing Rust CLIs through a small allowlisted command layer.

## What changed

`tauri-app/src-tauri/src/main.rs` now routes desktop commands to allowlisted Rust binaries:

- `omnibet-pack`
- `omnibet-infer`
- `omnibet-value`
- `omnibet-model`

No arbitrary command name is accepted by the desktop command surface.

## Commands wired

- `pack_summary` -> `omnibet-pack summary data_packs/football_core_v1`
- `predict_fixture` -> `omnibet-infer predict data_packs/football_core_v1 <home> <away>`
- `value_report` -> `omnibet-value report data_packs/football_core_v1 <home> <away> data/sample_odds_spain_cape_verde.csv 0.25`

The value report remains forced to low trust (`0.25`), so desktop output remains paper-only.

## CLI discovery

The bridge looks for CLI binaries in:

```text
rust-core/target/debug/
```

or in the directory specified by:

```text
OMNIBET_CLI_DIR
```

## Failure mode

If the binaries are not built yet, the Tauri command returns a structured `cli_missing` payload instead of crashing.

## CI check

`tools/check_ui_wiring.py` now checks:

- frontend tabs still exist;
- command names exist in frontend and Rust backend;
- paper-only/model-trust text exists;
- the backend uses `std::process::Command` directly;
- allowlisted binary names are present;
- low-trust value mode is forced.

## Honesty

This is still not a fully polished desktop app. It is the first hardened bridge from UI to the already-tested Rust runtime.
