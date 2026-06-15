# v18 Desktop UI Wiring Preview

v18 adds the first Tauri desktop UI wiring preview.

## New/updated files

```text
tauri-app/src-tauri/src/main.rs
tauri-app/src/index.html
tools/check_ui_wiring.py
```

## What is wired

Frontend tabs:

- Simple
- Detailed
- Advanced
- Bet Builder

Backend command stubs:

- `ping`
- `pack_summary`
- `predict_fixture`
- `value_report`

## Safety behavior

The UI explicitly stays paper-only. It includes model-trust and paper-only warnings and does not expose real-money staking labels.

## CI check

CI runs:

```bash
python tools/check_ui_wiring.py --root . --out reports/ci_ui_wiring.json
```

The check requires:

- every expected command appears in Rust and frontend code;
- every expected tab exists;
- paper-only/model-trust safety text exists;
- no profit-guarantee wording.

## Honesty

This is not a finished desktop app. It is the first bridge between the UI shell and backend command surface. The commands are safe stubs until the hardened desktop bridge calls the Rust model/value runtimes directly.
