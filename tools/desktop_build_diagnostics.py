#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from collections import deque
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


EXCLUDED_TREE_DIRS = {".git", "node_modules", "target", "__pycache__", ".pytest_cache", ".mypy_cache"}
DEFAULT_TIMEOUT_SECONDS = 600
FAILURE_TAIL_LINES = 140
FALLBACK_ICON_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABmJLR0QA/wD/AP+gvaeT"
    "AAAAoElEQVR4nO3QMQ0AAAgDoGn/0U9lB4GkG8mB0WbYmQAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAACsAeokewABoAUAAUAAUAAUAAUAAUAAUAAUAAUAAU"
    "AAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAAUAA"
    "UAAUAAUAB0zgMAAeMUrHUAAAAASUVORK5CYII="
)


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


def ensure_tauri_fallback_icons(root: Path) -> Dict[str, Any]:
    """Create tiny deterministic fallback icons for CI diagnostics when repo icons are absent."""
    icons_dir = root / "tauri-app" / "src-tauri" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    png_path = icons_dir / "icon.png"
    ico_path = icons_dir / "icon.ico"
    png_bytes = base64.b64decode(FALLBACK_ICON_PNG_B64)
    if not png_path.exists():
        png_path.write_bytes(png_bytes)
    if not ico_path.exists():
        # ICO container with one PNG-compressed 64x64 image. This is enough for tauri-build diagnostics.
        header = struct.pack("<HHH", 0, 1, 1)
        entry = struct.pack("<BBBBHHII", 64, 64, 0, 0, 1, 32, len(png_bytes), 22)
        ico_path.write_bytes(header + entry + png_bytes)
    return {
        "icon_png": {"path": rel(root, png_path), "exists": png_path.exists(), "size_bytes": png_path.stat().st_size},
        "icon_ico": {"path": rel(root, ico_path), "exists": ico_path.exists(), "size_bytes": ico_path.stat().st_size},
    }


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


def stream_pipe(pipe: Any, log_file: Any) -> None:
    """Stream command output into the per-command artifact log without flooding Actions console."""
    try:
        for line in iter(pipe.readline, ""):
            log_file.write(line)
            log_file.flush()
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def tail_text(path: Path, max_lines: int = FAILURE_TAIL_LINES) -> str:
    if not path.exists():
        return ""
    try:
        ring: deque[str] = deque(maxlen=max_lines)
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                ring.append(line.rstrip("\n"))
        return "\n".join(ring)
    except Exception as exc:  # pragma: no cover - diagnostics path
        return f"could not read log tail: {exc!r}"


def run_command(
    *,
    root: Path,
    out_dir: Path,
    name: str,
    command: str,
    cwd: Optional[Path] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    env_extra: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    started = time.time()
    log_path = out_dir / f"{name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
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
        "timeout_seconds": timeout_seconds,
        "started_at_unix": int(started),
    }

    timed_out = False
    status = 998
    print(f"DIAGNOSTIC_START name={name} cwd={header['cwd']} timeout={timeout_seconds}s", flush=True)
    with log_path.open("w", encoding="utf-8", errors="replace", buffering=1) as log_file:
        log_file.write("# OmniBet desktop build diagnostic command\n")
        log_file.write(json.dumps(header, indent=2, sort_keys=True))
        log_file.write("\n\n")
        log_file.flush()
        try:
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                env=env,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                errors="replace",
            )
            assert proc.stdout is not None
            reader = threading.Thread(target=stream_pipe, args=(proc.stdout, log_file), daemon=True)
            reader.start()
            deadline = started + timeout_seconds
            while proc.poll() is None:
                if time.time() > deadline:
                    timed_out = True
                    log_file.write(f"\nTIMEOUT: killed after {timeout_seconds} seconds\n")
                    log_file.flush()
                    proc.kill()
                    break
                time.sleep(1)
            status = proc.wait(timeout=30)
            reader.join(timeout=30)
            if timed_out:
                status = 124
        except Exception as exc:  # pragma: no cover - diagnostics path
            log_file.write(f"\ndiagnostic command spawn failed: {exc!r}\n")
            log_file.flush()
            status = 997
    finished = time.time()
    result = {
        **header,
        "finished_at_unix": int(finished),
        "duration_seconds": round(finished - started, 3),
        "status": status,
        "ok": status == 0,
        "timed_out": timed_out,
        "log": rel(root, log_path),
    }
    print(
        f"DIAGNOSTIC_RESULT name={name} status={status} ok={status == 0} "
        f"timed_out={timed_out} duration={result['duration_seconds']}s log={result['log']}",
        flush=True,
    )
    if status != 0:
        print(f"DIAGNOSTIC_FAILURE_TAIL_BEGIN name={name}", flush=True)
        print(tail_text(log_path), flush=True)
        print(f"DIAGNOSTIC_FAILURE_TAIL_END name={name}", flush=True)
    return result


def command_plan(root: Path) -> List[Dict[str, Any]]:
    tauri_app = root / "tauri-app"
    manifest = "tauri-app/src-tauri/Cargo.toml"
    return [
        {"name": "python-version", "command": f"{python_executable()} --version", "timeout_seconds": 60},
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


def python_executable() -> str:
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
        "tauri-app/src-tauri/icons/icon.ico",
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
    generated_assets = ensure_tauri_fallback_icons(root)

    summary: Dict[str, Any] = {
        "schema": "omnibet.desktop_build_diagnostics.v6",
        "root": str(root),
        "generated_assets": generated_assets,
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
            timeout_seconds=int(item.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
        )
        summary["commands"].append(result)
        write_json(out_dir / "build-status.json", summary)

    write_text(out_dir / "tauri-target-tree-after.txt", tree_snapshot(root, root / "tauri-app" / "src-tauri" / "target", 1000))
    write_text(out_dir / "tauri-bundle-tree-after.txt", tree_snapshot(root, root / "tauri-app" / "src-tauri" / "target" / "release" / "bundle", 1000))
    write_text(out_dir / "desktop-downloads-tree-after.txt", tree_snapshot(root, root / "build" / "desktop-downloads", 1000))

    summary["ok"] = all(cmd.get("ok") for cmd in summary["commands"])
    summary["failed_commands"] = [cmd for cmd in summary["commands"] if not cmd.get("ok")]
    write_json(out_dir / "build-status.json", summary)

    summary_lines = [
        f"schema={summary['schema']}",
        f"platform={summary['platform']['system']} {summary['platform']['release']} {summary['platform']['machine']}",
        f"ok={summary['ok']}",
        f"commands={len(summary['commands'])}",
        f"failed_commands={len(summary['failed_commands'])}",
    ]
    for cmd in summary["failed_commands"]:
        summary_lines.append(
            f"FAIL name={cmd['name']} status={cmd['status']} timed_out={cmd['timed_out']} log={cmd['log']}"
        )
    write_text(out_dir / "diagnostic-summary.txt", "\n".join(summary_lines) + "\n")
    print("DIAGNOSTIC_FINAL_SUMMARY_BEGIN", flush=True)
    print("\n".join(summary_lines), flush=True)
    print("DIAGNOSTIC_FINAL_SUMMARY_END", flush=True)


if __name__ == "__main__":
    main()
