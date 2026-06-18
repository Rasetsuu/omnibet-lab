#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path


def out_dir_from_argv(argv: list[str]) -> Path:
    for i, arg in enumerate(argv):
        if arg == "--out-dir" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if arg.startswith("--out-dir="):
            return Path(arg.split("=", 1)[1])
    return Path("build/desktop-diagnostics")


def main() -> None:
    out_dir = out_dir_from_argv(sys.argv[1:])
    try:
        runpy.run_path("tools/desktop_build_diagnostics.py", run_name="__main__")
    except SystemExit:
        raise
    except BaseException as exc:
        out_dir.mkdir(parents=True, exist_ok=True)
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        summary = (
            "schema=omnibet.desktop_build_diagnostics.wrapper_exception.v1\n"
            "ok=False\n"
            "commands=0\n"
            "failed_commands=1\n"
            f"FAIL name=desktop_build_diagnostics_wrapper status=997 timed_out=False log=build/desktop-diagnostics/wrapper-exception.log\n"
            f"exception={type(exc).__name__}: {exc}\n"
        )
        (out_dir / "diagnostic-summary.txt").write_text(summary, encoding="utf-8")
        (out_dir / "wrapper-exception.log").write_text(tb, encoding="utf-8")
        (out_dir / "build-status.json").write_text(
            '{"ok": false, "schema": "omnibet.desktop_build_diagnostics.wrapper_exception.v1"}\n',
            encoding="utf-8",
        )
        print("DIAGNOSTIC_WRAPPER_EXCEPTION_BEGIN", flush=True)
        print(summary, flush=True)
        print(tb, flush=True)
        print("DIAGNOSTIC_WRAPPER_EXCEPTION_END", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
