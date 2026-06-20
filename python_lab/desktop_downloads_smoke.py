#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def has(text: str, needle: str) -> bool:
    return needle in text


def build_report(root: Path) -> Dict[str, Any]:
    workflow_path = root / ".github/workflows/desktop_beta_builds.yml"
    manifest_path = root / "python_lab/desktop_build_manifest.py"
    config_path = root / "configs/desktop_downloads.v149_v156.json"
    notes_path = root / "docs/desktop_beta_release_notes_v149_v156.md"
    workflow = workflow_path.read_text(encoding="utf-8")
    manifest = manifest_path.read_text(encoding="utf-8")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    notes = notes_path.read_text(encoding="utf-8")
    checks = {
        "workflow_exists": workflow_path.exists(),
        "workflow_manual_only": has(workflow, "workflow_dispatch") and not has(workflow, "pull_request:") and not has(workflow, "push:"),
        "workflow_has_windows_linux": has(workflow, "windows-latest") and has(workflow, "ubuntu-latest"),
        "workflow_sets_node_rust": has(workflow, "actions/setup-node@v4") and has(workflow, "dtolnay/rust-toolchain@stable"),
        "workflow_installs_linux_deps": has(workflow, "libwebkit2gtk-4.1-dev") and has(workflow, "patchelf"),
        "workflow_runs_tauri_build": has(workflow, "npm run build") and has(workflow, "working-directory: tauri-app"),
        "workflow_uploads_artifacts": has(workflow, "actions/upload-artifact@v4") and has(workflow, "tauri-app/src-tauri/target/release/bundle/**"),
        "workflow_manifest_step": has(workflow, "desktop_build_manifest.py") and has(workflow, "DESKTOP_BUILD_MANIFEST.json"),
        "manifest_generator_exists": manifest_path.exists(),
        "manifest_generator_checksums": has(manifest, "sha256") and has(manifest, "hashlib.sha256"),
        "manifest_generator_discovers_bundle": has(manifest, "discover_files") and has(manifest, "artifact_count"),
        "config_exists": config_path.exists() and config.get("version") == "omnibet.desktop_downloads.v149_v156",
        "config_artifact_names": "windows" in config.get("artifact_names", {}) and "linux" in config.get("artifact_names", {}),
        "release_notes_exists": notes_path.exists() and has(notes, "Desktop Beta") and has(notes, "How to build"),
        "policy_no_credentials": config.get("policy", {}).get("credential_values") is False,
        "version_stable": config.get("desktop_version") == "0.6.0",
        "workflow_uses_lockfile_install": has(workflow, "npm ci") and has(workflow, "package-lock.json"),
        "workflow_builds_rust_cli_runtime": has(workflow, "cargo build --manifest-path rust-core/Cargo.toml --release --bins"),
        "workflow_stages_portable_package": has(workflow, "build/desktop-downloads/package") and has(workflow, "README_RUN.txt"),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.desktop_downloads_smoke.v149_v156",
        "milestone": "v149_v156_desktop_downloadable_builds",
        "acceptance": checks,
        "files": {
            "workflow": ".github/workflows/desktop_beta_builds.yml",
            "manifest_generator": "python_lab/desktop_build_manifest.py",
            "config": "configs/desktop_downloads.v149_v156.json",
            "release_notes": "docs/desktop_beta_release_notes_v149_v156.md",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v149_v156_desktop_downloads.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
