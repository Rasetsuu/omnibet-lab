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
    contract = read_json(root / "configs/desktop_release_artifacts.v481_v490.json")
    workflow = (root / contract["release_workflow"]).read_text(encoding="utf-8")
    policy = (root / "docs/beta_vs_model_quality_policy.md").read_text(encoding="utf-8")
    docs = (root / "docs/desktop_release_artifacts_v481_v490.md").read_text(encoding="utf-8")
    ci_workflow = (root / ".github/workflows/v481_v490_desktop_release_artifacts.yml").read_text(encoding="utf-8")
    package_json = read_json(root / "tauri-app/package.json")
    tauri_conf = read_json(root / "tauri-app/src-tauri/tauri.conf.json")
    acceptance = contract.get("acceptance", {})

    required_assets = contract.get("required_packaged_assets", [])
    required_bins = contract.get("required_runtime_bins", [])
    release_phrases = contract.get("release_notes_required_phrases", [])
    archive_expectations = contract.get("archive_expectations", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.desktop_release_artifacts_contract.v481_v490",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("desktop_beta_can_move_fast") is True and contract.get("model_training_must_move_slow") is True and contract.get("training_allowed") is False and contract.get("real_money_recommendations_allowed") is False,
        "release_workflow_dispatch_present": "workflow_dispatch" in workflow and "release_tag" in workflow,
        "release_archives_windows_linux": "OmniBet-Lab-Windows" in workflow and "OmniBet-Lab-Linux" in workflow and "Compress-Archive" in workflow and ".tar.gz" in workflow,
        "package_gui_samples": all(asset in workflow for asset in ["historical-materialization.sample.json", "historical-file-adapter.sample.json"]),
        "package_expected_asset_paths": all(asset in workflow for asset in required_assets),
        "package_historical_adapter_data": "data/historical/v451_v460" in workflow and "fixtures.adapter.sample.csv" in workflow and "identity_map.adapter.sample.csv" in workflow,
        "package_policy_docs": "docs/beta_vs_model_quality_policy.md" in workflow and "docs/desktop_beta_release_readiness_v471_v480.md" in workflow,
        "package_runtime_bins": all(bin_name in workflow for bin_name in required_bins),
        "readme_user_path": "README_RUN.txt" in workflow and archive_expectations.get("windows_app_name") in workflow and "./omnibet-lab" in workflow,
        "readme_lists_new_gui_panels": "Historical Materialization" in workflow and "Historical File Adapter" in workflow and "Calibration / CLV" in workflow,
        "release_notes_safety_language": all(phrase in workflow for phrase in release_phrases),
        "release_notes_download_path": "Download the archive for your platform" in workflow and "Windows: `OmniBet-Lab.exe`" in workflow and "Linux: `./omnibet-lab`" in workflow,
        "github_release_create_update": "gh release create" in workflow and "gh release upload" in workflow and "gh release edit" in workflow,
        "draft_prerelease_defaults": 'default: "true"' in workflow and "--prerelease" in workflow and "--draft" in workflow,
        "manifest_in_archive": "DESKTOP_BUILD_MANIFEST.json" in workflow and "desktop_build_manifest.py" in workflow,
        "version_alignment_ok": package_json.get("version") == tauri_conf.get("version"),
        "policy_doc_still_strict": "GUI beta can move fast" in policy and "Prediction/training engine must move slow" in policy and "never bypass trust gates" in policy,
        "docs_updated": "v481-v490 Desktop Release Artifacts" in docs and "v0.6.0-beta.1" in docs and "Releases" in docs,
        "ci_workflow_updated": "desktop_release_artifact_flow_smoke.py" in ci_workflow and "compile_python_sources.py" in ci_workflow and "upload-artifact" in ci_workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.desktop_release_artifact_flow_smoke.v481_v490",
        "milestone": "v481_v490_github_release_artifacts_downloadable_beta_flow",
        "acceptance": checks,
        "summary": {
            "workflow": contract.get("release_workflow"),
            "release_tag_example": archive_expectations.get("release_tag_example"),
            "windows_archive_suffix": archive_expectations.get("windows_archive_suffix"),
            "linux_archive_suffix": archive_expectations.get("linux_archive_suffix"),
            "package_version": package_json.get("version"),
            "tauri_version": tauri_conf.get("version"),
            "required_asset_count": len(required_assets),
            "required_runtime_bin_count": len(required_bins),
            "training_allowed": contract.get("training_allowed"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v481_v490_desktop_release_artifacts.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
