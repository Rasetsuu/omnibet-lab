# v257 Desktop Source View

v257 wires the source report into the desktop app.

## Added pieces

```text
tauri-app/src-tauri/src/main.rs
tauri-app/src/api.js
tauri-app/src/source_terminal.js
tauri-app/src/source-terminal.sample.json
tauri-app/src/index.html
tauri-app/src/app.js
```

## Page and controls

```text
page: source-terminal
buttons: load-source-terminal-report, load-source-terminal-sample
panels: source-terminal-summary, source-terminal-readiness, source-terminal-actions, source-terminal-blockers
```

## Sample status

```text
adapter count: 2
adapter OK count: 2
normalized total rows: 5
odds snapshot candidates: 3
fixture result candidates: 1
event context candidates: 1
```

## Safety

The page is read-only and paper-only. It shows local report status and bundled sample data for inspection.

## Next batch

v258 should add a local report generation workflow that writes the source report into `.omnibet-local/reports/` for the desktop loader.
