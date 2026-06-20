# OmniBet Lab Desktop Beta 0.6.0

This is a desktop beta layout for local/offline research workflows. It is still a **paper-only** research preview, not a betting recommendation product.

## Included

- Tauri desktop dashboard shell.
- Desktop Beta page.
- Local CSV/JSON/JSONL import preview.
- Local import integrity summary.
- Local import bundle export.
- Model/evaluation sample panels.
- Report/checklist sample panels.
- Windows and Linux manual build workflow.
- Portable runtime package that stages the Rust CLIs beside the desktop app.

## Build artifacts

The manual GitHub Actions workflow `OmniBet Desktop Beta Builds` builds desktop artifacts on:

- `windows-latest`
- `ubuntu-latest`

Each artifact upload includes:

- `build/desktop-downloads/package/**` — portable app directory for quick beta testing.
- `DESKTOP_BUILD_MANIFEST.json` — file names, sizes, and SHA256 checksums.
- `tauri-app/src-tauri/target/release/bundle/**` — native Tauri bundle outputs when produced by the runner.

## Runtime layout

The portable package includes:

```text
OmniBet-Lab.exe / omnibet-lab
omnibet-pack(.exe)
omnibet-infer(.exe)
omnibet-value(.exe)
omnibet-model(.exe)
bin/
rust-core/target/debug/  # compatibility path for current Tauri bridge
data/
data_packs/football_core_v1/
README_RUN.txt
```

The current Tauri backend still expects the developer-style `rust-core/target/debug` runtime path unless `OMNIBET_CLI_DIR` is set, so the portable package stages the release-built CLIs into that compatibility path as well as beside the app and in `./bin`.

## Dependency policy

No `tauri-app/package-lock.json` is committed yet. The workflow intentionally uses `npm install --foreground-scripts --loglevel warn` because the current desktop shell has only `@tauri-apps/cli` as a dev dependency. Before a production release, generate a lockfile from a normal developer environment and switch CI to `npm ci`.

## Limits

- This is not a final product release.
- This is not a live-source production app.
- Outputs are research previews, not recommendations.
- Local files are user-provided.
- No credential values are stored in the repository.
- Accuracy and edge are not proven until larger no-future-leak backtests, calibration, no-vig bookmaker baselines, and CLV validation pass.

## How to build

Run the manual workflow from GitHub Actions:

1. Open Actions.
2. Choose `OmniBet Desktop Beta Builds`.
3. Click `Run workflow`.
4. Download the Windows/Linux artifacts after the run completes.
5. Unzip the artifact and run the app from the `package` directory.
