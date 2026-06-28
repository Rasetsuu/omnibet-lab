# v481-v490 Desktop Release Artifacts

This phase hardens the downloadable beta release flow so the GitHub Releases page can contain usable Windows/Linux archives.

## Included versions

```text
v481 release artifact contract
v482 package GUI sample assets
v483 package historical adapter sample data
v484 package research policy docs
v485 package runtime CLI runners
v486 release README user path
v487 release notes beta safety language
v488 Windows/Linux archive expectations
v489 CI release artifact flow smoke
v490 release artifact docs
```

## What this changes

The existing release workflow remains:

```text
.github/workflows/desktop_release.yml
```

It already supports manual release creation via `workflow_dispatch`. This phase hardens what goes inside the downloadable archives.

## Release tag example

Use a beta tag such as:

```text
v0.6.0-beta.1
```

When the desktop release workflow is run with that tag, it should create or update a GitHub Release and upload platform archives.

## Expected release assets

```text
OmniBet-Lab-Windows-v0.6.0-beta.1.zip
OmniBet-Lab-Linux-v0.6.0-beta.1.tar.gz
```

These should appear under the repository **Releases** page after the workflow publishes the release.

## Expected user path

Windows:

```text
download zip
extract
run OmniBet-Lab.exe
```

Linux:

```text
download tar.gz
extract
run ./omnibet-lab
```

## Packaged beta assets

The release package includes GUI and local-data assets needed for the new beta pages:

```text
tauri-app/src/historical-materialization.sample.json
tauri-app/src/historical-file-adapter.sample.json
data/historical/v451_v460/fixtures.adapter.sample.csv
data/historical/v451_v460/odds.adapter.sample.csv
data/historical/v451_v460/settlements.adapter.sample.csv
data/historical/v451_v460/identity_map.adapter.sample.csv
docs/beta_vs_model_quality_policy.md
```

It also includes release/runtime CLIs:

```text
omnibet-pack
omnibet-infer
omnibet-value
omnibet-model
omnibet-local-import-runner
omnibet-historical-materialization-runner
```

## Safety language

The release package and notes must keep:

```text
PAPER_ONLY
not betting recommendations
not staking advice
not proof of edge
GUI beta can move fast
prediction/training engine must move slow
```

Training remains locked:

```text
ready_for_training = false
training_allowed = false
```

## Important distinction

This phase does not itself publish a release. It hardens and verifies the workflow that publishes a release.

After this PR lands, the next action is to run the desktop release workflow with a beta tag like `v0.6.0-beta.1`. That workflow is what will make the release appear on the GitHub Releases page.

## Next

After this, the next phase should be:

```text
v491-v500 Beta QA checklist + offline demo dataset
```

or directly run the manual `OmniBet Desktop Release` workflow for a first beta artifact if CI is clean.
