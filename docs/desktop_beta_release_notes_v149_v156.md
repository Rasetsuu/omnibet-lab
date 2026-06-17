# OmniBet Lab Desktop Beta 0.6.0-rc.1

This is a desktop beta layout for local/offline research workflows.

## Included

- Desktop dashboard shell.
- Desktop Beta page.
- Local CSV/JSON/JSONL import preview.
- Local import integrity summary.
- Local import bundle export.
- Model/evaluation sample panels.
- Report/checklist sample panels.
- Windows and Linux manual build workflow.

## Build artifacts

The manual GitHub Actions workflow `OmniBet Desktop Beta Builds` builds desktop artifacts on:

- `windows-latest`
- `ubuntu-latest`

Each artifact upload includes a `DESKTOP_BUILD_MANIFEST.json` with file names, sizes, and SHA256 checksums.

## Limits

- This is not a final product release.
- This is not a live-source production app.
- Outputs are research previews, not recommendations.
- Local files are user-provided.
- No credential values are stored in the repository.

## How to build

Run the manual workflow from GitHub Actions:

1. Open Actions.
2. Choose `OmniBet Desktop Beta Builds`.
3. Click `Run workflow`.
4. Download the Windows/Linux artifacts after the run completes.
