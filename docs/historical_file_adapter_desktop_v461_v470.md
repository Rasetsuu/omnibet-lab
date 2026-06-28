# v461-v470 Historical File Adapter Desktop

This phase turns the v451-v460 historical file adapter report into a visible desktop GUI panel.

It is directly aimed at the downloadable Windows/Linux beta path: users need pages they can click, not only backend smoke scripts.

## Included versions

```text
v461 desktop file adapter report contract
v462 adapter catalog loader panel
v463 fixture CSV preview panel
v464 odds CSV preview panel
v465 settlement CSV preview panel
v466 identity CSV preview panel
v467 adapter validation errors panel
v468 adapter training lock panel
v469 CI adapter desktop smoke
v470 adapter desktop docs
```

## Page

The desktop page is:

```text
Historical File Adapter
historical-file-adapter
```

The renderer self-registers the navigation item, topbar button, page, and panels before `app.js` binds events. This avoids rewriting the large desktop HTML file and reduces risk to older pages.

## Renderer

```text
tauri-app/src/historical_file_adapter.js
```

It loads generated adapter output first:

```text
reports/historical_file_adapter_v451_v460_report.json
reports/historical_file_adapter_v451_v460_normalized_preview.json
```

If generated files are not present, it falls back to:

```text
tauri-app/src/historical-file-adapter.sample.json
```

## Panels

```text
historical-file-adapter-summary
historical-file-adapter-inputs
historical-file-adapter-fixtures
historical-file-adapter-odds
historical-file-adapter-settlements
historical-file-adapter-identities
historical-file-adapter-errors
historical-file-adapter-trust
```

## Safety locks

The adapter panel can show local CSV previews and validation state, but it does not unlock training.

```text
ready_for_materialization = true
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

## Why this matters for beta

This is one of the last missing user-visible pieces before packaging work:

```text
local historical CSV adapter visible in GUI
generated materialization visible in GUI
training still locked
no live provider calls
```

The next release-focused phase should be:

```text
v471-v480 Desktop beta release readiness for Windows/Linux
```

That should inspect the existing Tauri package flow, release workflow, app metadata, and downloadable artifacts.
