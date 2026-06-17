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
    "tauri-app/src/models.js",
    "tauri-app/src/app.js",
    "tauri-app/src/dashboard-data.sample.json",
    "tauri-app/src/review-data.sample.json",
    "tauri-app/src/settings-data.sample.json",
    "tauri-app/src/phase2-forecast.sample.json",
    "tauri-app/src-tauri/tauri.conf.json",
    "tauri-app/src-tauri/Cargo.toml",
    "tauri-app/src-tauri/src/main.rs",
    "tauri-app/package.json",
    "configs/local_data_contract.v61.json",
    "configs/desktop_local_foundation.v58_v61.json",
    "configs/desktop_package_readiness.v57.json",
    "configs/desktop_rc_packaging.v62.json",
    "docs/v57_desktop_package_readiness.md",
    "docs/v58_v61_desktop_local_foundation.md",
    "docs/v62_desktop_rc_packaging.md",
]

README = f"""# OmniBet Lab Desktop {EXPECTED_DESKTOP_VERSION}

Portable desktop RC layout.

Run for development:

```text
cd tauri-app
npm install
npm run dev
```

Local data root defaults to `.omnibet-local/` and can be overridden with `OMNIBET_HOME`.

This package is paper/offline-first and includes no secret values.
"""

WINDOWS = """# Windows

```text
cd tauri-app
npm install
npm run dev
```

Python override: `OMNIBET_PYTHON`.
"""

LINUX = """# Linux

```text
cd tauri-app
npm install
npm run dev
```

Python override: `OMNIBET_PYTHON`.
"""

SAFETY = """# Safety

Paper/offline-first package. No secret values are included. Review decisions stay local.
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
    dst = release_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, dst)
    return {"path": rel, "bytes": dst.stat().st_size, "sha256": sha256_file(dst)}


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def make_zip(source_dir: Path, zip_path: Path) -> str:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in iter_files(source_dir):
            info = zipfile.ZipInfo(path.relative_to(source_dir.parent).as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    return sha256_file(zip_path)


def build_package(root: Path, out_dir: Path) -> Dict[str, Any]:
    preflight = build_package_report(root, "release_packaging")
    release_root = out_dir / PACKAGE_NAME
    if release_root.exists():
        shutil.rmtree(release_root)
    release_root.mkdir(parents=True, exist_ok=True)
    included = [copy_file(root, rel, release_root) for rel in INCLUDE_FILES]
    docs = {"README_RUN.md": README, "WINDOWS.md": WINDOWS, "LINUX.md": LINUX, "SAFETY.md": SAFETY}
    generated = []
    for rel, text in docs.items():
        path = release_root / rel
        write_text(path, text)
        generated.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "ok": True,
        "schema": "omnibet.desktop_rc_manifest.v62_plus_v72",
        "package_name": PACKAGE_NAME,
        "desktop_version": EXPECTED_DESKTOP_VERSION,
        "release_kind": "portable_rc_layout",
        "contains_signed_installer": False,
        "contains_runtime_binary": False,
        "package_preflight_ok": preflight.get("ok"),
        "included_files": included,
        "generated_docs": generated,
        "entrypoints": {"tauri_frontend": "tauri-app/src/index.html", "phase2_ui_sample": "tauri-app/src/phase2-forecast.sample.json"},
        "known_limits": ["not a signed installer", "no runtime binary included", "phase2 sample is small and offline"],
        "safety": {"paper_only": True, "offline_default": True, "no_secret_values": True, "no_recommendation_output": True},
    }
    manifest_path = release_root / "RELEASE_MANIFEST.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
    zip_path = out_dir / f"{PACKAGE_NAME}.zip"
    return {"ok": True, "package_name": PACKAGE_NAME, "release_dir": str(release_root), "zip_path": str(zip_path), "zip_sha256": make_zip(release_root, zip_path), "manifest_path": str(manifest_path), "manifest": manifest, "package_preflight": preflight}


def build_report(root: Path, out_dir: Path) -> Dict[str, Any]:
    package = build_package(root, out_dir)
    manifest = package["manifest"]
    checks = {
        "package_ok": package.get("ok") is True,
        "preflight_ok": package["package_preflight"].get("ok") is True,
        "zip_exists": Path(package["zip_path"]).exists(),
        "manifest_exists": Path(package["manifest_path"]).exists(),
        "version_rc": manifest.get("desktop_version") == EXPECTED_DESKTOP_VERSION,
        "has_required_sources": len(manifest.get("included_files", [])) == len(INCLUDE_FILES),
        "has_phase2_asset": any(x.get("path") == "tauri-app/src/phase2-forecast.sample.json" for x in manifest.get("included_files", [])),
        "no_binary_claim": manifest.get("contains_runtime_binary") is False,
        "no_installer_claim": manifest.get("contains_signed_installer") is False,
        "checksums_present": bool(package.get("zip_sha256")) and bool(manifest.get("manifest_sha256")),
    }
    return {"ok": all(checks.values()), "milestone": "v62_plus_v72_desktop_rc_packaging", "package_name": package["package_name"], "release_dir": package["release_dir"], "zip_path": package["zip_path"], "zip_sha256": package["zip_sha256"], "manifest_path": package["manifest_path"], "acceptance": checks, "safety": manifest["safety"], "known_limits": manifest["known_limits"]}


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
