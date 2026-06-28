#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def explicit_safety_flags_ok(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False)
    return (
        '"credential_values_present": true' not in serialized
        and '"recommendation_output_present": true' not in serialized
        and '"ready_for_training": true' not in serialized
        and '"training_allowed": true' not in serialized
        and '"real_money_recommendations_allowed": true' not in serialized
    )


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/desktop_beta_release_readiness.v471_v480.json")
    tauri_conf = read_json(root / "tauri-app/src-tauri/tauri.conf.json")
    package_json = read_json(root / "tauri-app/package.json")
    release_workflow = (root / ".github/workflows/desktop_release.yml").read_text(encoding="utf-8")
    build_manifest = (root / "python_lab/desktop_build_manifest.py").read_text(encoding="utf-8")
    policy = (root / "docs/beta_vs_model_quality_policy.md").read_text(encoding="utf-8")
    docs = (root / "docs/desktop_beta_release_readiness_v471_v480.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v471_v480_desktop_beta_release_readiness.yml").read_text(encoding="utf-8")
    expectations = contract.get("release_expectations", {})
    package_expectations = contract.get("package_expectations", {})
    acceptance = contract.get("acceptance", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.desktop_beta_release_readiness_contract.v471_v480",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("desktop_beta_can_move_fast") is True and contract.get("model_training_must_move_slow") is True and contract.get("training_allowed") is False and contract.get("real_money_recommendations_allowed") is False,
        "policy_doc_present": "GUI beta can move fast" in policy and "Prediction/training engine must move slow" in policy and "never bypass trust gates" in policy,
        "release_workflow_dispatch": "workflow_dispatch" in release_workflow and "release_tag" in release_workflow,
        "release_workflow_windows_linux": expectations.get("windows_runner_required") in release_workflow and expectations.get("linux_runner_required") in release_workflow,
        "release_workflow_builds_tauri": "npm run build" in release_workflow and "tauri build" in (root / "tauri-app/package.json").read_text(encoding="utf-8"),
        "release_workflow_builds_rust_bins": "cargo build --manifest-path rust-core/Cargo.toml --release --bins" in release_workflow,
        "release_assets_created": "build/release-assets" in release_workflow and "Compress-Archive" in release_workflow and "tar -C build/desktop-release" in release_workflow,
        "github_release_publish_step": "gh release create" in release_workflow and "gh release upload" in release_workflow,
        "release_safety_notes": "PAPER_ONLY" in release_workflow and "not betting recommendations" in release_workflow and "not staking advice" in release_workflow,
        "tauri_metadata_ok": tauri_conf.get("productName") == package_expectations.get("product_name") and tauri_conf.get("identifier") == package_expectations.get("identifier"),
        "version_alignment_ok": tauri_conf.get("version") == package_json.get("version"),
        "bundle_targets_ok": tauri_conf.get("bundle", {}).get("active") is True and tauri_conf.get("bundle", {}).get("targets") == package_expectations.get("bundle_targets"),
        "portable_package_has_run_readme": "README_RUN.txt" in release_workflow and "OmniBet-Lab.exe" in release_workflow and "run-omnibet-lab-linux.sh" in release_workflow,
        "build_manifest_has_hashes": "sha256" in build_manifest and "artifact_count" in build_manifest and "desktop_download_manifest" in build_manifest,
        "docs_updated": "v471-v480 Desktop Beta Release Readiness" in docs and "Windows" in docs and "Linux" in docs and "ready_for_training = false" in docs,
        "workflow_updated": "desktop_beta_release_readiness_smoke.py" in workflow and "compile_python_sources.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.desktop_beta_release_readiness_smoke.v471_v480",
        "milestone": "v471_v480_windows_linux_desktop_beta_release_readiness",
        "acceptance": checks,
        "summary": {
            "product_name": tauri_conf.get("productName"),
            "tauri_version": tauri_conf.get("version"),
            "package_version": package_json.get("version"),
            "windows_runner": expectations.get("windows_runner_required"),
            "linux_runner": expectations.get("linux_runner_required"),
            "release_workflow": expectations.get("workflow_path"),
            "training_allowed": contract.get("training_allowed"),
            "desktop_beta_can_move_fast": contract.get("desktop_beta_can_move_fast"),
            "model_training_must_move_slow": contract.get("model_training_must_move_slow"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v471_v480_desktop_beta_release_readiness.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
