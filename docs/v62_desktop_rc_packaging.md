# v62 Desktop Release Candidate Packaging

v62 adds the first desktop release-candidate packaging layer.

It creates a deterministic portable RC layout instead of a signed installer.

## Version

```text
0.6.0
```

Synced across:

```text
tauri-app/src-tauri/tauri.conf.json
tauri-app/src-tauri/Cargo.toml
tauri-app/package.json
```

## Package layout

The packaging smoke creates:

```text
build/desktop_rc_v62/omnibet-lab-desktop-0.6.0/
  README_RUN.md
  WINDOWS.md
  LINUX.md
  SAFETY.md
  RELEASE_MANIFEST.json
  tauri-app/...
  configs/...
  docs/...
```

and:

```text
build/desktop_rc_v62/omnibet-lab-desktop-0.6.0.zip
```

## Manifest

`RELEASE_MANIFEST.json` includes:

```text
package name
desktop version
included files
per-file sha256 hashes
manifest sha256
run instructions
known limitations
safety policy
```

## Not yet included

```text
signed Windows installer
AppImage/deb/rpm
runtime desktop binary
code signing
live provider configuration
```

Those are intentionally deferred until the packaging/signing/dependency strategy is locked.

## Smoke

```bash
python python_lab/desktop_rc_packaging_smoke.py \
  --root . \
  --out-dir build/desktop_rc_v62 \
  --out reports/ci_v62_desktop_rc_packaging.json
```

The smoke checks:

```text
package preflight is green
release directory exists
zip artifact exists
manifest exists
checksums are present
run docs are included
safety policy is included
no installer/binary claim is made
```

## Safety

```text
PAPER_ONLY.
Offline by default.
No API key values.
No live provider calls required.
No recommendation output.
No shell execution.
```
