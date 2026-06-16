# v57 Windows/Linux Desktop Package Readiness

v57 adds lightweight cross-platform readiness checks for the Tauri/Rust desktop path.

This milestone intentionally does **not** run a full Linux Tauri bundle yet. Full Linux bundling often requires system WebKit packages and distribution-specific setup. v57 verifies the package shape and command wiring first.

## What is checked

```text
Tauri config parses
Cargo package version matches Tauri app version
static frontend files exist
frontend modules are linked from index.html
no web server command is required
bundle config is active
Rust/Tauri commands are registered
allowlisted local workflows are present
no shell execution markers exist
PathBuf/Path are used for local paths
Windows/Linux Python selection is present
sample dashboard/review/settings JSON parses
PAPER_ONLY marker remains present
```

## Version

v57 bumps the desktop app package metadata to:

```text
0.4.0
```

in both:

```text
tauri-app/src-tauri/tauri.conf.json
tauri-app/src-tauri/Cargo.toml
```

## Cross-platform CI

The dedicated workflow runs the same static readiness smoke on:

```text
ubuntu-latest
windows-latest
```

Smoke command:

```bash
python python_lab/desktop_package_readiness_smoke.py \
  --root . \
  --platform-name "$RUNNER_OS" \
  --out reports/ci_v57_desktop_package_readiness.json
```

On Windows, the workflow passes `Windows` explicitly.

## Safety

```text
No API keys.
No live provider calls.
No network provider calls.
No recommendation output.
No shell execution.
No web-server dependency for the static frontend.
```

## Future packaging step

A later milestone can add full installer/bundle jobs once Linux dependencies and Windows signing/package strategy are explicitly configured.
