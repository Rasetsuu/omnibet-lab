#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def discover_files(bundle_dir: Path) -> List[Dict[str, Any]]:
    if not bundle_dir.exists():
        return []
    rows = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        rows.append({
            "path": str(path),
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
        })
    return rows


def build_manifest(root: Path, bundle_dir: Path, platform: str, build_label: str) -> Dict[str, Any]:
    tauri_conf = json.loads((root / "tauri-app/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    package_json = json.loads((root / "tauri-app/package.json").read_text(encoding="utf-8"))
    files = discover_files(bundle_dir)
    return {
        "ok": len(files) > 0,
        "schema": "omnibet.desktop_download_manifest.v149_v156",
        "product_name": tauri_conf.get("productName"),
        "desktop_version": tauri_conf.get("version"),
        "package_version": package_json.get("version"),
        "platform": platform,
        "build_label": build_label,
        "bundle_dir": str(bundle_dir),
        "artifact_count": len(files),
        "artifacts": files,
        "policy": {
            "desktop_beta": True,
            "offline_first": True,
            "credential_values": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--bundle-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--platform", default="unknown")
    ap.add_argument("--build-label", default="manual-beta")
    args = ap.parse_args()
    manifest = build_manifest(Path(args.root), Path(args.bundle_dir), args.platform, args.build_label)
    write_json(Path(args.out), manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if not manifest["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
