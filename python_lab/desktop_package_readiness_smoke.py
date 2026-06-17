#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

EXPECTED_DESKTOP_VERSION = "0.6.0-rc.1"

FRONTEND_FILES = [
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
    "tauri-app/src/model-lab.sample.json",
    "tauri-app/src/competition-lab.sample.json",
    "tauri-app/src/league-universe.sample.json",
]

REQUIRED_COMMANDS = ["ping", "load_dashboard_report", "load_review_report", "load_app_settings", "run_local_workflow", "save_review_decision", "pack_summary", "predict_fixture", "value_report"]
REQUIRED_MODULES = ["api.js", "dashboard.js", "review.js", "settings.js", "models.js", "app.js"]
REQUIRED_WORKFLOWS = ["generate_dashboard_report", "generate_review_report", "run_leak_guard", "run_feature_export", "run_settlement_truth", "run_first_model_pass"]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def parse_cargo_version(cargo: str) -> str | None:
    match = re.search(r'^version\s*=\s*"([^"]+)"', cargo, flags=re.MULTILINE)
    return match.group(1) if match else None


def load_package_json(root: Path) -> Dict[str, Any]:
    path = root / "tauri-app/package.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def package_has_no_web_server(package: Dict[str, Any]) -> bool:
    combined = json.dumps({"scripts": package.get("scripts", {}), "dependencies": package.get("dependencies", {}), "devDependencies": package.get("devDependencies", {})}).lower()
    return not any(word in combined for word in ["vite", "webpack", "next", "serve", "http-server", "dev-server"])


def build_report(root: Path, platform_name: str) -> Dict[str, Any]:
    tauri_conf = json.loads(read(root, "tauri-app/src-tauri/tauri.conf.json"))
    cargo = read(root, "tauri-app/src-tauri/Cargo.toml")
    rust = read(root, "tauri-app/src-tauri/src/main.rs")
    html = read(root, "tauri-app/src/index.html")
    settings = json.loads(read(root, "tauri-app/src/settings-data.sample.json"))
    review = json.loads(read(root, "tauri-app/src/review-data.sample.json"))
    dashboard = json.loads(read(root, "tauri-app/src/dashboard-data.sample.json"))
    phase2 = json.loads(read(root, "tauri-app/src/phase2-forecast.sample.json"))
    model_lab = json.loads(read(root, "tauri-app/src/model-lab.sample.json"))
    comp_lab = json.loads(read(root, "tauri-app/src/competition-lab.sample.json"))
    league_universe = json.loads(read(root, "tauri-app/src/league-universe.sample.json"))
    package = load_package_json(root)

    file_presence = {rel: (root / rel).exists() for rel in FRONTEND_FILES}
    cargo_version = parse_cargo_version(cargo)
    tauri_version = tauri_conf.get("version")
    package_version = package.get("version")
    module_links = {module: f'src="{module}"' in html for module in REQUIRED_MODULES}
    command_registration = {cmd: (f"fn {cmd}" in rust and cmd in rust and "generate_handler!" in rust) for cmd in REQUIRED_COMMANDS}
    workflow_allowlist = {workflow: workflow in rust for workflow in REQUIRED_WORKFLOWS}

    checks = {
        "all_frontend_files_present": all(file_presence.values()),
        "tauri_config_valid_json": isinstance(tauri_conf, dict),
        "product_name_present": tauri_conf.get("productName") == "OmniBet Lab",
        "identifier_present": tauri_conf.get("identifier") == "local.omnibet.lab",
        "cargo_tauri_and_package_versions_match": cargo_version == tauri_version == package_version == EXPECTED_DESKTOP_VERSION,
        "frontend_dist_static_src": tauri_conf.get("build", {}).get("frontendDist") == "../src",
        "no_before_build_web_server": tauri_conf.get("build", {}).get("beforeBuildCommand") == "" and tauri_conf.get("build", {}).get("beforeDevCommand") == "",
        "package_metadata_has_no_web_server_dependency": package_has_no_web_server(package),
        "package_is_private": package.get("private") is True,
        "package_has_tauri_cli_only": set((package.get("dependencies") or {}).keys()) == set() and set((package.get("devDependencies") or {}).keys()) == {"@tauri-apps/cli"},
        "bundle_active": tauri_conf.get("bundle", {}).get("active") is True,
        "bundle_targets_all": tauri_conf.get("bundle", {}).get("targets") == "all",
        "window_size_present": len(tauri_conf.get("app", {}).get("windows", [])) >= 1,
        "all_modules_linked": all(module_links.values()),
        "paper_only_marker": "PAPER_ONLY" in html,
        "all_commands_registered": all(command_registration.values()),
        "workflow_allowlist_present": all(workflow_allowlist.values()),
        "review_decision_persistence_present": "review_decisions/review_decisions.jsonl" in rust and "save_review_decision" in rust,
        "local_data_contract_present": "OMNIBET_HOME" in rust and ".omnibet-local" in rust,
        "workflow_ux_fields_present": all(s in rust for s in ["state", "started_at_unix", "finished_at_unix", "report_path_hint", "refresh_hint", "stdout_preview", "stderr_preview"]),
        "model_phase_sample_present": phase2.get("ok") is True and phase2.get("registry", {}).get("schema") == "omnibet.model_registry.v71",
        "model_lab_sample_present": model_lab.get("ok") is True and model_lab.get("model_lab", {}).get("schema") == "omnibet.model_lab_payload.v78",
        "competition_lab_sample_present": comp_lab.get("ok") is True and comp_lab.get("competition_lab", {}).get("schema") == "omnibet.competition_model_lab.v86",
        "league_universe_sample_present": league_universe.get("ok") is True and league_universe.get("row_counts", {}).get("total", 0) >= 45,
        "no_shell_execution": ".shell" not in rust and "cmd /C" not in rust and "sh -c" not in rust,
        "direct_command_invocation": "Command::new" in rust,
        "pathbuf_used": "PathBuf" in rust and "Path::new" in rust,
        "windows_python_branch": "cfg!(windows)" in rust and '"python".to_string()' in rust,
        "linux_python_branch": '"python3".to_string()' in rust,
        "python_env_override": "OMNIBET_PYTHON" in rust,
        "cli_dir_env_override": "OMNIBET_CLI_DIR" in rust,
        "samples_parse": all(x.get("ok") is True for x in [dashboard, review, settings, phase2, model_lab, comp_lab, league_universe]),
        "settings_no_key_values": settings.get("safety", {}).get("no_api_key_values") is True,
        "settings_no_network": settings.get("runtime", {}).get("network_enabled") is False,
    }
    checks["platform_specific_python_choice_visible"] = "cfg!(windows)" in rust if platform_name.lower().startswith("win") else '"python3".to_string()' in rust
    return {"ok": all(checks.values()), "milestone": "v86b_league_universe_package_readiness", "platform": platform_name, "tauri_version": tauri_version, "cargo_version": cargo_version, "package_version": package_version, "file_presence": file_presence, "module_links": module_links, "command_registration": command_registration, "workflow_allowlist": workflow_allowlist, "acceptance": checks, "safety": {"offline_static_checks_only": True, "no_api_keys": True, "no_network_provider_calls": True, "no_shell_execution": checks["no_shell_execution"], "no_web_server_dependency": checks["no_before_build_web_server"] and checks["package_metadata_has_no_web_server_dependency"]}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--platform-name", default=os.environ.get("RUNNER_OS", os.name))
    ap.add_argument("--out", default="reports/ci_v62_desktop_package_readiness.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), args.platform_name)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
