#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

COMMANDS = ["ping", "pack_summary", "predict_fixture", "value_report"]
TABS = ["simple", "detailed", "advanced", "builder"]
ALLOWLIST = ["omnibet-pack", "omnibet-infer", "omnibet-value", "omnibet-model"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_ui_wiring.json")
    args = ap.parse_args()
    root = Path(args.root)
    main_rs = root / "tauri-app" / "src-tauri" / "src" / "main.rs"
    html = root / "tauri-app" / "src" / "index.html"

    rust = main_rs.read_text(encoding="utf-8")
    page = html.read_text(encoding="utf-8")

    commands = {cmd: (f"fn {cmd}" in rust and cmd in page) for cmd in COMMANDS}
    tabs = {tab: (f'id="{tab}"' in page) for tab in TABS}
    safety = {
        "paper_only_text": "paper-only" in page.lower() or "PAPER_ONLY" in page,
        "model_trust_present": "model_trust" in page or "model_trust" in rust,
        "no_profit_claim": "profit guarantee" not in page.lower(),
    }
    bridge = {
        "uses_process_command": "std::process::Command" in rust and "Command::new" in rust,
        "has_allowlist": all(x in rust for x in ALLOWLIST),
        "has_cli_missing_mode": "cli_missing" in rust,
        "has_blocked_mode": "blocked" in rust,
        "forces_low_trust_value": '"0.25".to_string()' in rust,
        "no_shell_import": "use std::process::Command" in rust,
    }
    out = {
        "ok": all(commands.values()) and all(tabs.values()) and all(safety.values()) and all(bridge.values()),
        "commands": commands,
        "tabs": tabs,
        "safety": safety,
        "bridge": bridge,
    }
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not out["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
