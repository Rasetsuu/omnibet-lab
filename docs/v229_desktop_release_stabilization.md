# v229 Desktop release stabilization

v229 turns the desktop beta build from a developer-oriented Tauri bundle into a more realistic downloadable beta artifact.

## Goals

- Keep the manual desktop build workflow manual-only.
- Remove the generated icon fallback and avoid requiring missing icon files during build.
- Document the temporary no-lockfile policy and keep the workflow on explicit npm install until v230 can add a clean lockfile.
- Build the Rust CLI runtime in release mode before packaging.
- Stage omnibet-pack, omnibet-infer, omnibet-value, and omnibet-model with the desktop executable.
- Stage the tiny sample odds CSV and compressed football data pack needed by the current desktop buttons.
- Remove committed local junk artifacts that can be regenerated.
- Update the README to reflect the v181-v228 beta train plus v229 packaging stabilization.

## Runtime layout

The current Tauri backend still uses the developer-style CLI lookup path unless OMNIBET_CLI_DIR is set. v229 keeps that backend stable and makes the portable package match it by staging release-built CLIs in:

```text
rust-core/target/debug/
```

The same CLIs are also copied beside the app and into bin/ so a later backend cleanup can switch to a cleaner lookup without changing the package shape.

## Safety

The app remains paper-only. Packaging work does not claim model edge, staking confidence, or production data-source readiness.
