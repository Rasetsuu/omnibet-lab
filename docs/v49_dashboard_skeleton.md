# v49 GUI Dashboard Skeleton

v49 adds the first offline GUI/dashboard skeleton for the provider pipeline.

It extends the existing dependency-free Tauri frontend at:

```text
tauri-app/src/index.html
```

and adds a static browser/Tauri preview payload:

```text
tauri-app/src/dashboard-data.sample.json
```

## Dashboard sections

The dashboard exposes six panels:

```text
event list
market snapshots
unknown market queue
feature snapshot preview
settlement report
result accounting report
```

Each panel is backed by the same offline pipeline shape proven by v35-v48.

## Data smoke

The dashboard smoke builds a compact JSON payload from the offline pipeline:

```bash
cd python_lab
python dashboard_data_smoke.py \
  --db ../build/omnibet_v49_dashboard.sqlite \
  --dashboard-out ../build/v49_dashboard_data.json \
  --ui-path ../tauri-app/src/index.html \
  --out ../reports/ci_v49_dashboard_data.json
```

The smoke validates:

```text
all required dashboard sections exist
event rows are present
market rows are present
unknown queue rows are present
feature preview rows are present
settlement rows are present
result accounting rows are present
Tauri HTML file exists
Tauri HTML contains dashboard section markers
```

## UI behavior

In browser preview, the dashboard loads:

```text
dashboard-data.sample.json
```

If the static JSON is unavailable, it falls back to a small embedded preview object.

Future versions can connect the dashboard to Tauri commands that read local generated reports.

## Safety

```text
Offline samples only.
No API keys.
No live provider calls.
No network in CI.
No recommendation output.
```
