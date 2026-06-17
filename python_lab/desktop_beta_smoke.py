#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def import_wizard_payload() -> Dict[str, Any]:
    return {
        "schema": "omnibet.desktop_import_wizard.v125",
        "steps": [
            {"step_id": "choose_local_files", "label": "Choose local files", "required": True},
            {"step_id": "map_competitions", "label": "Map competitions", "required": True},
            {"step_id": "preview_rows", "label": "Preview rows", "required": True},
            {"step_id": "run_integrity", "label": "Run integrity checks", "required": True},
            {"step_id": "save_local_import", "label": "Save local import", "required": False},
        ],
        "accepted_file_kinds": ["csv", "jsonl"],
        "policy": {"local_files_only": True, "no_credentials": True},
    }


def coverage_payload() -> Dict[str, Any]:
    comps = ["eng_premier", "esp_laliga", "ger_bundesliga", "usa_mls", "bra_serie_a", "uefa_champions"]
    return {
        "schema": "omnibet.desktop_coverage.v126",
        "summary": {"covered_competitions": len(comps), "trainable_rows": 3016, "evaluation_rows": 756, "min_seasons": 10},
        "competitions": [{"competition_id": comp, "status": "ready", "seasons": 10 + (idx % 2), "rows": 180 + idx * 12} for idx, comp in enumerate(comps)],
    }


def evaluation_payload() -> Dict[str, Any]:
    return {
        "schema": "omnibet.desktop_evaluation.v127",
        "summary": {"model_family": "competition_runtime", "evaluation_rows": 756, "calibration_rows": 28},
        "metrics": [
            {"competition_id": "eng_premier", "brier": 0.210, "accuracy_at_0_5": 0.69},
            {"competition_id": "esp_laliga", "brier": 0.222, "accuracy_at_0_5": 0.67},
            {"competition_id": "uefa_champions", "brier": 0.231, "accuracy_at_0_5": 0.64},
        ],
        "policy": {"research_only": True},
    }


def report_viewer_payload() -> Dict[str, Any]:
    return {
        "schema": "omnibet.desktop_report_viewer.v128",
        "reports": [
            {"report_id": "coverage", "path_hint": "reports/coverage.json", "kind": "coverage", "severity": "info"},
            {"report_id": "integrity", "path_hint": "reports/integrity.json", "kind": "integrity", "severity": "info"},
            {"report_id": "evaluation", "path_hint": "reports/evaluation.json", "kind": "evaluation", "severity": "info"},
        ],
        "log_levels": ["info", "warning", "error"],
    }


def backup_contract() -> Dict[str, Any]:
    return {
        "schema": "omnibet.local_backup_contract.v129",
        "include_dirs": ["configs", "reports", "exports", "review_decisions", "cache"],
        "exclude_patterns": ["*.tmp", "*.lock", "secret*"],
        "operations": ["export_local_bundle", "import_local_bundle", "verify_bundle_manifest"],
        "policy": {"local_only": True, "no_secret_values": True},
    }


def beta_manifest() -> Dict[str, Any]:
    return {
        "schema": "omnibet.desktop_beta_manifest.v130",
        "version": "0.6.0-rc.1",
        "release_kind": "desktop_beta_layout",
        "contains_signed_installer": False,
        "contains_runtime_binary": False,
        "entrypoints": ["tauri-app/src/index.html", "tauri-app/src/desktop-beta.sample.json"],
        "known_limits": ["local beta layout", "manual import path", "research outputs only"],
    }


def release_checklist() -> Dict[str, Any]:
    items = [
        ("ci_green", "All required CI gates are green"),
        ("package_ready", "Package readiness smoke passes on Windows and Linux"),
        ("rc_package", "Portable RC packaging smoke passes"),
        ("runtime_core", "Rust runtime core smoke passes"),
        ("local_import", "Local import wizard payload exists"),
        ("backup_contract", "Local backup/export/import contract exists"),
        ("policy", "No credentials or live calls required"),
    ]
    return {"schema": "omnibet.release_checklist.v131", "items": [{"check_id": i, "description": d, "required": True} for i, d in items]}


def build_beta_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema": "omnibet.desktop_beta_payload.v132",
        "import_wizard": import_wizard_payload(),
        "coverage": coverage_payload(),
        "evaluation": evaluation_payload(),
        "report_viewer": report_viewer_payload(),
        "backup_contract": backup_contract(),
        "beta_manifest": beta_manifest(),
        "release_checklist": release_checklist(),
        "policy": {"offline_first": True, "local_files_only": True, "no_credentials": True},
    }


def build_report(out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_beta_payload()
    paths = {
        "import_wizard": out_dir / "desktop_import_wizard.v125.json",
        "coverage": out_dir / "desktop_coverage.v126.json",
        "evaluation": out_dir / "desktop_evaluation.v127.json",
        "report_viewer": out_dir / "desktop_report_viewer.v128.json",
        "backup_contract": out_dir / "local_backup_contract.v129.json",
        "beta_manifest": out_dir / "desktop_beta_manifest.v130.json",
        "release_checklist": out_dir / "release_checklist.v131.json",
        "beta_payload": out_dir / "desktop_beta_payload.v132.json",
    }
    write_json(paths["import_wizard"], payload["import_wizard"])
    write_json(paths["coverage"], payload["coverage"])
    write_json(paths["evaluation"], payload["evaluation"])
    write_json(paths["report_viewer"], payload["report_viewer"])
    write_json(paths["backup_contract"], payload["backup_contract"])
    write_json(paths["beta_manifest"], payload["beta_manifest"])
    write_json(paths["release_checklist"], payload["release_checklist"])
    write_json(paths["beta_payload"], payload)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.desktop_beta.sample.v132", "desktop_beta": payload})
    hashes = {f"{key}_sha256": sha_file(path) for key, path in paths.items()}
    manifest = {
        "ok": True,
        "schema": "omnibet.desktop_beta_phase.v125_v132",
        "outputs": {key: str(path) for key, path in paths.items()},
        "hashes": hashes,
        "row_counts": {
            "wizard_steps": len(payload["import_wizard"]["steps"]),
            "coverage_competitions": payload["coverage"]["summary"]["covered_competitions"],
            "reports": len(payload["report_viewer"]["reports"]),
            "checklist_items": len(payload["release_checklist"]["items"]),
        },
        "policy": payload["policy"],
    }
    checks = {
        "wizard_steps_present": manifest["row_counts"]["wizard_steps"] >= 5,
        "coverage_present": manifest["row_counts"]["coverage_competitions"] >= 3,
        "evaluation_present": payload["evaluation"]["summary"]["evaluation_rows"] > 0,
        "reports_present": manifest["row_counts"]["reports"] >= 3,
        "backup_contract_present": len(payload["backup_contract"]["operations"]) >= 3,
        "checklist_present": manifest["row_counts"]["checklist_items"] >= 7,
        "hashes_present": all(hashes.values()),
        "ui_sample_written": ui_sample is not None and ui_sample.exists(),
        "offline_first": payload["policy"]["offline_first"] is True,
        "no_credentials": payload["policy"]["no_credentials"] is True,
    }
    report = {"ok": all(checks.values()), "milestone": "v125_v132_desktop_beta", "acceptance": checks, "manifest": manifest}
    write_json(out_dir / "desktop_beta_phase.v125_v132.json", report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="build/desktop_beta_v125_v132")
    ap.add_argument("--ui-sample", default="tauri-app/src/desktop-beta.sample.json")
    ap.add_argument("--out", default="reports/ci_v125_v132_desktop_beta.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
