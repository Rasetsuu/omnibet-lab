# CI and Local Test Workflow

OmniBet now has a one-command test harness plus GitHub Actions CI.

## Local test

From the repository root:

```bash
bash tools/run_all_local_tests.sh
```

This rebuilds the SQLite warehouse, exports/verifies packs, runs the synthetic event demo, runs Rust tests, runs Rust model/value smoke checks, and writes:

```text
reports/ci_summary.json
```

## GitHub Actions

The workflow lives at:

```text
.github/workflows/ci.yml
```

It runs automatically on:

- push
- pull request
- manual workflow dispatch

## What CI checks

- Python scripts compile.
- SQLite warehouse can be rebuilt from the CSV fixture.
- Core football pack can be exported and verified.
- Synthetic event demo pack can be exported and verified.
- Rust `cargo test` passes.
- Rust pack verifier accepts both packs.
- Rust baseline/gold comparison has aligned test windows.
- Rust value report uses low-trust `PAPER ONLY` gating.

## Why this matters

This allows bigger development batches. Instead of manually running every command after each small change, GitHub Actions can run the full test harness and expose logs/reports for review.

## Workflow refresh

After enabling Actions on a new private repository, make any small commit or use the manual workflow button in GitHub Actions to start the first run.
