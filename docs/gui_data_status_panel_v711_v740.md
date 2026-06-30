# v711-v740 GUI Data Status Panel

This phase adds a passive data pipeline status card to the normal Matches screen.

## Visible status

```text
Data pipeline
Local sample runner      Wired in Rust CI
Normalized sample pack   Available from local files
Real model               Locked until enough settled rows
Network/live calls       Off in normal beta flow
```

## Scope

The panel is status-only.

It does not expose training or import buttons in the normal GUI.

## Files

```text
tauri-app/src/simple_matches.js
configs/gui_data_status_panel.v711_v740.json
python_lab/gui_data_status_panel_smoke.py
```
