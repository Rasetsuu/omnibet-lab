#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from desktop_package_readiness_smoke import EXPECTED_DESKTOP_VERSION, build_report as build_package_report

PACKAGE_NAME = f"omnibet-lab-desktop-{EXPECTED_DESKTOP_VERSION}"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

INCLUDE_FILES = [
    "tauri-app/src/index.html",
    "tauri-app/src/styles.css",
    "tauri-app/src/api.js",
    "tauri-app/src/dashboard.js",
    "tauri-app/src/review.js",
    "tauri-app/src/settings.js",
    "tauri-app/src/app.js",
    "tauri-app/src/dashboard-data.sample.json",
    "tauri-app/src/review-data.sample.json",
    "tauri-app/src/settings-data.sample.json",
    "tauri-app/src-tauri/tauri.conf.json",
    "tauri-app/src-tauri/Cargo.toml",
    "tauri-app/src-tauri/src/main.rs",
    "tauri-app/package.json",
    "configs/local_data_contract.v61.json",
    "configs/desktop_local_foundation.v58_v61.json",
    "configs/desktop_package_readiness.v57.json",
    "docs/v57_desktop_package_readiness.md",
    "docs/v58_v61_desktop_local_foundation.md",
]

RUN_README = f"""# OmniBet Lab Desktop {EXPECTED_DESKTOP_VERSION}

This is the first portable desktop release-candidate layout.

It is not a signed installer yet. It packages the desktop source layout, static frontend, Tauri/Rust bridge source, sample data, safety docs, and local data contract so Windows/Linux packaging can be finalized in a later milestone.

## Safety

- PAPER_ONLY research app.
- Offline/local by default.
- No live provider calls are required.
- No API key values are included.
- No recommendation output is produced by this package.

## Local data root

Default:

```text
.omnibet-local/
```

Override:

```text
OMNIBET_HOME=/path/to/OmniBetLocal
```

## Developer run path

Install Rust, Node, and Tauri prerequisites for your OS, then from the repository root:

```text
cd tauri-app
npm install
npm run dev
```

Full installer packaging is intentionally deferred until the platform dependency/signing strategy is locked.
"""

WINDOWS_DOC = """# Windows RC Notes

This RC is a portable source/package layout, not a signed MSI/NSIS installer yet.

Recommended local dev command:

```text
cd tauri-app
npm install
npm run dev
```

Python selection in the desktop bridge:

```text
OMNIBET_PYTHON if set
python otherwise on Windows
```

No API key values should be committed or displayed.
"""

LINUX_DOC = """# Linux RC Notes

This RC is a portable source/package layout, not an AppImage/deb/rpm yet.

Recommended local dev command:

```text
cd tauri-app
npm install
npm run dev
```

Linux Tauri bundling can require WebKit/system packages, so full installer bundling is deferred to a later milestone.

Python selection in the desktop bridge:

```text
OMNIBET_PYTHON if set
python3 otherwise on Linux
```
"""

SAFETY_DOC = """# Safety Policy

OmniBet Lab desktop RC is offline/local-first.

Rules:

```text
No API key values in package files.
No live provider calls in CI.
No network provider calls in packaging checks.
No shell execution path.
No recommendation output.
Review decisions persist locally only.
```
"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(root: Path, rel: str, release_root: Path) -> Dict[str, Any]:
    src = root / rel
    dst = release_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"path": rel, "bytes": dst.stat().st_size, "sha256": sha256_file(dst)}


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def make_deterministic_zip(source_dir: Path, zip_path: Path) -> str:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in iter_files(source_dir):
            rel = path.relative_to(source_dir.parent).as_posix()
            info = zipfile.ZipInfo(rel, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            data = path.read_bytes()
            zf.writestr(info, data)
    return sha256_file(zip_path)


def build_package(root: Path, out_dir: Path) -> Dict[str, Any]:
    package_report = build_package_report(root, "release_packaging")
    release_root = out_dir / PACKAGE_NAME
    if release_root.exists():
        shutil.rmtree(release_root)
    release_root.mkdir(parents=True, exist_ok=True)

    copied: List[Dict[str, Any]] = []
    for rel in INCLUDE_FILES:
        copied.append(copy_file(root, rel, release_root))

    write_text(release_root / "README_RUN.md", RUN_README)
    write_text(release_root / "WINDOWS.md", WINDOWS_DOC)
    write_text(release_root / "LINUX.md", LINUX_DOC)
    write_text(release_root / "SAFETY.md", SAFETY_DOC)

    generated_docs = []
    for rel in ["README_RUN.md", "WINDOWS.md", "LINUX.md", "SAFETY.md"]:
        path = release_root / rel
        generated_docs.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})

    manifest = {
        "ok": True,
        "schema": "omnibet.desktop_rc_manifest.v62",
        "package_name": PACKAGE_NAME,
        "desktop_version": EXPECTED_DESKTOP_VERSION,
        "release_kind": "portable_rc_layout",
        "contains_signed_installer": False,
        "contains_runtime_binary": False,
        "package_preflight_ok": package_report.get("ok"),
        "included_files": copied,
        "generated_docs": generated_docs,
        "entrypoints": {
            "tauri_frontend": "tauri-app/src/index.html",
            "tauri_config": "tauri-app/src-tauri/tauri.conf.json",
            "local_data_contract": "configs/local_data_contract.v61.json"
        },
        "run_instructions": {
            "windows": "cd tauri-app && npm install && npm run dev",
            "linux": "cd tauri-app && npm install && npm run dev"
        },
        "known_limits": [
            "not a signed installer",
            "no AppImage/deb/MSI/NSIS artifact yet",
            "live providers remain opt-in future work",
            "review decision promotion to production mappings remains future work"
        ],
        "safety": {
            "paper_only": True,
            "offline_default": True,
            "no_api_key_values": True,
            "no_live_provider_calls_required": True,
            "no_recommendation_output": True,
            "no_shell_execution": True
        }
    }
    manifest_path = release_root / "RELEASE_MANIFEST.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    zip_path = out_dir / f"{PACKAGE_NAME}.zip"
    zip_sha = make_deterministic_zip(release_root, zip_path)
    return {
        "ok": True,
        "package_name": PACKAGE_NAME,
        "release_dir": str(release_root),
        "zip_path": str(zip_path),
        "zip_sha256": zip_sha,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "package_preflight": package_report,
    }


def build_report(root: Path, out_dir: Path) -> Dict[str, Any]:
    package = build_package(root, out_dir)
    manifest = package["manifest"]
    zip_path = Path(package["zip_path"])
    checks = {
        "package_ok": package.get("ok") is True,
        "preflight_ok": package["package_preflight"].get("ok") is True,
        "zip_exists": zip_path.exists() and zip_path.stat().st_size > 0,
        "manifest_exists": Path(package["manifest_path"]).exists(),
        "version_rc": manifest.get("desktop_version") == EXPECTED_DESKTOP_VERSION,
        "has_run_docs": all((Path(package["release_dir"]) / rel).exists() for rel in ["README_RUN.md", "WINDOWS.md", "LINUX.md", "SAFETY.md"]),
        "has_required_sources": len(manifest.get("included_files", [])) == len(INCLUDE_FILES),
        "no_binary_claim": manifest.get("contains_runtime_binary") is False,
        "no_installer_claim": manifest.get("contains_signed_installer") is False,
        "safety_ok": all(manifest.get("safety", {}).values()),
        "checksums_present": bool(package.get("zip_sha256")) and bool(manifest.get("manifest_sha256")),
    }
    return {
        "ok": all(checks.values()),
        "milestone": "v62_desktop_release_candidate_packaging",
        "package_name": package["package_name"],
        "release_dir": package["release_dir"],
        "zip_path": package["zip_path"],
        "zip_sha256": package["zip_sha256"],
        "manifest_path": package["manifest_path"],
        "acceptance": checks,
        "safety": manifest["safety"],
        "known_limits": manifest["known_limits"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="build/desktop_rc_v62")
    ap.add_argument("--out", default="reports/ci_v62_desktop_rc_packaging.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.out_dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
