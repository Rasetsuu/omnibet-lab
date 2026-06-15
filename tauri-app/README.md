# OmniBet Lab Tauri App Skeleton

This is the planned desktop GUI path for OmniBet Lab.

Why Tauri:
- Reuse the browser GUI / HTML/JS frontend.
- Keep heavy and stable logic in Rust commands.
- Package for Windows and Linux with a small native wrapper.

Status in v3A:
- Skeleton only.
- The production GUI should call Rust commands for:
  - implied probability / overround removal
  - EV/Kelly
  - Poisson/Dixon-Coles inference
  - SQLite feature-store reads
  - bet-builder generation

Training remains Python-side for now because the ML ecosystem is stronger there.
