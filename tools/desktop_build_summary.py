#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def tail_text(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return f"missing log: {path}\n"
    data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(data[-lines:]) + "\n"


def run_command(root: Path, out_dir: Path, name: str, command: str, cwd: Optional[Path], timeout_seconds: int) -> Dict[str, Any]:
    started = time.time()
    log_path = out_dir / f"{name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cwd = cwd or root
    env = os.environ.copy()
    env.update({"RUST_BACKTRACE": "full", "CARGO_TERM_COLOR": "always"})
    header = {"name": name, "command": command, "cwd": rel(root, cwd), "timeout_seconds": timeout_seconds}
    print(f"START {name}: {command}")
    status = 998
    timed_out = False
    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        log_file.write(json.dumps(header, indent=2, sort_keys=True) + "\n\n")
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd),
                env=env,
                shell=True,
                text=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
            )
            status = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            status = 124
            log_file.write(f"\nTIMEOUT after {timeout_seconds} seconds\n")
        except Exception as exc:
            status = 997
            log_file.write(f"\ncommand failed to start: {exc!r}\n")
    duration = round(time.time() - started, 3)
    print(f"DONE {name}: status={status} duration={duration}s log={rel(root, log_path)}")
    return {**header, "status": status, "ok": status == 0, "timed_out": timed_out, "duration_seconds": duration, "log": rel(root, log_path)}


def command_plan(root: Path) -> List[Dict[str, Any]]:
    tauri_app = root / "tauri-app"
    manifest = "tauri-app/src-tauri/Cargo.toml"
    py = sys.executable.replace("\\", "/")
    return [
        {"name": "python-version", "command": f"{py} --version", "timeout_seconds": 60},
        {"name": "node-version", "command": "node --version", "timeout_seconds": 60},
        {"name": "npm-version", "command": "npm --version", "timeout_seconds": 60},
        {"name": "rustc-version", "command": "rustc --version --verbose", "timeout_seconds": 60},
        {"name": "cargo-version", "command": "cargo --version --verbose", "timeout_seconds": 60},
        {"name": "cargo-metadata-tauri", "command": f"cargo metadata --manifest-path {manifest} --format-version 1", "cwd": root, "timeout_seconds": 180},
        {"name": "npm-install-tauri", "command": "npm install --foreground-scripts --loglevel verbose", "cwd": tauri_app, "timeout_seconds": 600},
        {"name": "npx-tauri-info", "command": "npx tauri info", "cwd": tauri_app, "timeout_seconds": 300},
        {"name": "npm-build-tauri-no-bundle", "command": "npm run build -- --no-bundle", "cwd": tauri_app, "timeout_seconds": 1200},
        {"name": "npm-build-tauri-bundle", "command": "npm run build", "cwd": tauri_app, "timeout_seconds": 1200},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="build/desktop-diagnostics")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {"schema": "omnibet.desktop_build_summary.v1", "commands": []}
    for item in command_plan(root):
        result = run_command(root, out_dir, item["name"], item["command"], item.get("cwd"), int(item.get("timeout_seconds", 600)))
        summary["commands"].append(result)
        write_json(out_dir / "build-status.json", summary)
    summary["ok"] = all(cmd["ok"] for cmd in summary["commands"])
    summary["failed_commands"] = [cmd for cmd in summary["commands"] if not cmd["ok"]]
    write_json(out_dir / "build-status.json", summary)
    print("DESKTOP_BUILD_SUMMARY")
    print(json.dumps({"ok": summary["ok"], "failed_commands": summary["failed_commands"]}, indent=2, sort_keys=True))
    for cmd in summary["failed_commands"]:
        print(f"--- tail: {cmd['log']} ---")
        print(tail_text(root / cmd["log"], 80))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
