#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


EXCLUDED_TREE_DIRS = {".git", "node_modules", "target", "__pycache__", ".pytest_cache", ".mypy_cache"}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def safe_env() -> Dict[str, str]:
    keep_prefixes = (
        "CI",
        "GITHUB_",
        "RUNNER_",
        "Image",
        "ImageOS",
        "ImageVersion",
        "PATH",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "RUST",
        "CARGO",
        "NODE",
        "NPM",
        "TAURI",
        "WEBKIT",
    )
    blocked_fragments = ("TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL", "AUTH")
    out: Dict[str, str] = {}
    for k, v in sorted(os.environ.items()):
        if any(fragment in k.upper() for fragment in blocked_fragments):
            continue
        if k.startswith(keep_prefixes) or k in {"OS", "PROCESSOR_ARCHITECTURE", "SHELL"}:
            out[k] = v
    return out


def tree_snapshot(root: Path, path: Path, max_entries: int = 500) -> str:
    lines: List[str] = []
    if not path.exists():
        return f"MISSING: {rel(root, path)}\n"
    count = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDED_TREE_DIRS]
        files = sorted(files)
        current_path = Path(current)
        depth = len(current_path.relative_to(path).parts) if current_path != path else 0
        if depth > 6:
            dirs[:] = []
            continue
        for name in files:
            p = current_path / name
            try:
                size = p.stat().st_size
            except OSError:
                size = -1
            lines.append(f"{rel(root, p)}\t{size}")
            count += 1
            if count >= max_entries:
                lines.append(f"...truncated after {max_entries} entries...")
                return "\n".join(lines) + "\n"
    return "\n".join(lines) + ("\n" if lines else "")


def run_command(
    *,
    root: Path,
    out_dir: Path,
    name: str,
    command: str,
    cwd: Optional[Path] = None,
    env_extra: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    started = time.time()
    log_path = out_dir / f"{name}.log"
    cwd = cwd or root
    env = os.environ.copy()
    env.update(
        {
            "RUST_BACKTRACE": "full",
            "CARGO_TERM_VERBOSE": "true",
            "CARGO_TERM_COLOR": "always",
            "NPM_CONFIG_FOREGROUND_SCRIPTS": "true",
        }
    )
    if env_extra:
        env.update(env_extra)
    header = {
        "name": name,
        "command": command,
        "cwd": rel(root, cwd),
        "started_at_unix": int(started),
    }
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            errors="replace",
        )
        output = proc.stdout or ""
        status = proc.returncode
    except Exception as exc:  # pragma: no cover - diagnostics path
        output = f"diagnostic command spawn failed: {exc!r}\n"
        status = 997
    finished = time.time()
    write_text(
        log_path,
        "# OmniBet desktop build diagnostic command\n"
        + json.dumps(header, indent=2, sort_keys=True)
        + "\n\n"
        + output,
    )
    return {
        **header,
        "finished_at_unix": int(finished),
        "duration_seconds": round(finished - started, 3),
        "status": status,
        "ok": status == 0,
        "log": rel(root, log_path),
    }


def command_plan(root: Path) -> List[Dict[str, Any]]:
    src_tauri = root / "tauri-app" / "src-tauri"
    tauri_app = root / "tauri-app"
    manifest = "tauri-app/src-tauri/Cargo.toml"
    return [
        {"name": "python-version", "command": f"{shlex_py()} --version"},
        {"name": "node-version", "command": "node --version"},
        {"name": "npm-version", "command": "npm --version"},
        {"name": "rustc-version", "command": "rustc --version --verbose"},
        {"name": "cargo-version", "command": "cargo --version --verbose"},
        {"name": "cargo-metadata-tauri", "command": f"cargo metadata --manifest-path {manifest} --format-version 1", "cwd": root},
        {"name": "cargo-check-tauri", "command": f"cargo check --manifest-path {manifest} -vv", "cwd": root},
        {"name": "cargo-build-tauri-debug", "command": f"cargo build --manifest-path {manifest} -vv", "cwd": root},
        {"name": "cargo-build-tauri-release", "command": f"cargo build --manifest-path {manifest} --release -vv", "cwd": root},
        {"name": "npm-install-tauri", "command": "npm install --foreground-scripts --loglevel verbose", "cwd": tauri_app},
        {"name": "npx-tauri-info", "command": "npx tauri info", "cwd": tauri_app},
        {"name": "npm-build-tauri-no-bundle", "command": "npm run build -- --no-bundle", "cwd": tauri_app},
        {"name": "npm-build-tauri-bundle", "command": "npm run build", "cwd": tauri_app},
    ]


def shlex_py() -> str:
    # On GitHub Actions this resolves to the active setup-python interpreter path.
    return sys.executable.replace("\\", "/")


def file_probe(root: Path) -> Dict[str, Any]:
    paths = [
        "tauri-app/package.json",
        "tauri-app/package-lock.json",
        "tauri-app/src/index.html",
        "tauri-app/src-tauri/Cargo.toml",
        "tauri-app/src-tauri/build.rs",
        "tauri-app/src-tauri/tauri.conf.json",
        "tauri-app/src-tauri/capabilities/default.json",
        "tauri-app/src-tauri/icons/icon.png",
        "rust-core/Cargo.toml",
        "data/sample_prices.csv",
        "data/sample_odds_spain_cape_verde.csv",
    ]
    out: Dict[str, Any] = {}
    for item in paths:
        p = root / item
        out[item] = {
            "exists": p.exists(),
            "is_file": p.is_file(),
            "size_bytes": p.stat().st_size if p.exists() and p.is_file() else None,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="build/desktop-diagnostics")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "schema": "omnibet.desktop_build_diagnostics.v1",
        "root": str(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": sys.version,
            "executable": sys.executable,
        },
        "which": {
            "python": shutil.which("python"),
            "python3": shutil.which("python3"),
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
            "npx": shutil.which("npx"),
            "rustc": shutil.which("rustc"),
            "cargo": shutil.which("cargo"),
        },
        "file_probe": file_probe(root),
        "safe_environment": safe_env(),
        "commands": [],
    }
    write_json(out_dir / "environment.json", summary)
    write_text(out_dir / "repo-tree.txt", tree_snapshot(root, root, 800))
    write_text(out_dir / "tauri-tree-before.txt", tree_snapshot(root, root / "tauri-app", 800))
    write_text(out_dir / "rust-core-tree-before.txt", tree_snapshot(root, root / "rust-core", 800))

    for item in command_plan(root):
        result = run_command(
            root=root,
            out_dir=out_dir,
            name=item["name"],
            command=item["command"],
            cwd=item.get("cwd"),
        )
        summary["commands"].append(result)
        write_json(out_dir / "build-status.json", summary)

    write_text(out_dir / "tauri-target-tree-after.txt", tree_snapshot(root, root / "tauri-app" / "src-tauri" / "target", 1000))
    write_text(out_dir / "tauri-bundle-tree-after.txt", tree_snapshot(root, root / "tauri-app" / "src-tauri" / "target" / "release" / "bundle", 1000))
    write_text(out_dir / "desktop-downloads-tree-after.txt", tree_snapshot(root, root / "build" / "desktop-downloads", 1000))

    summary["ok"] = all(cmd.get("ok") for cmd in summary["commands"])
    summary["failed_commands"] = [cmd for cmd in summary["commands"] if not cmd.get("ok")]
    write_json(out_dir / "build-status.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
