# v50-v52 Desktop GUI Architecture and Dashboard Bridge

This milestone moves the GUI away from the one-file web-preview concept and toward the desktop-first Tauri path.

## v50 GUI architecture cleanup

The frontend is split into dedicated files:

```text
tauri-app/src/index.html
tauri-app/src/styles.css
tauri-app/src/api.js
tauri-app/src/dashboard.js
tauri-app/src/app.js
```

`index.html` now acts as the desktop shell and keeps the required `PAPER_ONLY` safety marker.

## v51 Tauri dashboard report command

The Rust backend adds:

```rust
load_dashboard_report(path_hint: Option<String>)
```

It loads local dashboard JSON from allowlisted paths:

```text
build/v49_dashboard_data.json
reports/ci_v49_dashboard_data.json
tauri-app/src/dashboard-data.sample.json
```

No network or provider calls are used.

## v52 Desktop navigation layout

The frontend now has a sidebar layout with pages:

```text
Dashboard
Events
Markets
Unknown Queue
Features
Settlement
Accounting
Models
Settings
Simple
Detailed
Advanced
Market Builder
```

The Dashboard page renders the same six v49 panels:

```text
event list
market snapshots
unknown market queue
feature snapshot preview
settlement report
result accounting report
```

## Smoke

```bash
python python_lab/desktop_gui_bridge_smoke.py \
  --root . \
  --out reports/ci_v50_v52_desktop_gui_bridge.json
```

The smoke checks:

```text
frontend files exist
HTML links the split CSS/JS modules
sidebar/page markers exist
all dashboard markers exist
Tauri dashboard command is registered
Rust command reads local files only
sample dashboard JSON contains required sections
PAPER_ONLY marker remains present
```

## Safety

```text
Offline/local files only.
No API keys.
No live provider calls.
No network in CI.
No recommendation output.
```
