#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path


VALID_64_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAJ0lEQVR42u3BAQ0AAADCoPdPbQ43oAAAAAAAAAAAAAAAAAAAAIB3A0BAAAGveg7oAAAAAElFTkSuQmCC"


def out_dir_from_argv(argv: list[str]) -> Path:
    for i, arg in enumerate(argv):
        if arg == "--out-dir" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if arg.startswith("--out-dir="):
            return Path(arg.split("=", 1)[1])
    return Path("build/desktop-diagnostics")


def normalize_fallback_icon_constant() -> None:
    """Patch the diagnostics script in-place if an older invalid icon literal is present."""
    path = Path("tools/desktop_build_diagnostics.py")
    text = path.read_text(encoding="utf-8")
    marker = "FALLBACK_ICON_PNG_B64 = ("
    start = text.find(marker)
    if start == -1 or VALID_64_PNG_B64 in text:
        return
    end = text.find("\n)\n", start)
    if end == -1:
        return
    end += len("\n)\n")
    replacement = f'FALLBACK_ICON_PNG_B64 = (\n    "{VALID_64_PNG_B64}"\n)\n'
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def main() -> None:
    out_dir = out_dir_from_argv(sys.argv[1:])
    try:
        normalize_fallback_icon_constant()
        runpy.run_path("tools/desktop_build_diagnostics.py", run_name="__main__")
    except SystemExit:
        raise
    except BaseException as exc:
        out_dir.mkdir(parents=True, exist_ok=True)
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        summary = (
            "schema=omnibet.desktop_build_diagnostics.wrapper_exception.v2\n"
            "ok=False\n"
            "commands=0\n"
            "failed_commands=1\n"
            f"FAIL name=desktop_build_diagnostics_wrapper status=997 timed_out=False log=build/desktop-diagnostics/wrapper-exception.log\n"
            f"exception={type(exc).__name__}: {exc}\n"
        )
        (out_dir / "diagnostic-summary.txt").write_text(summary, encoding="utf-8")
        (out_dir / "wrapper-exception.log").write_text(tb, encoding="utf-8")
        (out_dir / "build-status.json").write_text(
            '{"ok": false, "schema": "omnibet.desktop_build_diagnostics.wrapper_exception.v2"}\n',
            encoding="utf-8",
        )
        print("DIAGNOSTIC_WRAPPER_EXCEPTION_BEGIN", flush=True)
        print(summary, flush=True)
        print(tb, flush=True)
        print("DIAGNOSTIC_WRAPPER_EXCEPTION_END", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
