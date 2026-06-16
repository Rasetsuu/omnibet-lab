#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict


def load_contract(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def local_root(contract: Dict[str, Any], override: str | None = None) -> Path:
    if override:
        return Path(override)
    env_name = contract.get("root_env", "OMNIBET_HOME")
    if os.environ.get(env_name):
        return Path(os.environ[env_name])
    return Path(contract.get("default_root", ".omnibet-local"))


def materialize(contract_path: Path, root_override: str | None = None, create: bool = False) -> Dict[str, Any]:
    contract = load_contract(contract_path)
    root = local_root(contract, root_override)
    dirs = {name: root / rel for name, rel in contract.get("directories", {}).items()}
    files = {name: root / rel for name, rel in contract.get("files", {}).items()}
    if create:
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
    return {
        "ok": True,
        "contract_version": contract.get("version"),
        "root": str(root),
        "directories": {name: str(path) for name, path in dirs.items()},
        "files": {name: str(path) for name, path in files.items()},
        "created": create,
        "policy": contract.get("policy", {}),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default="configs/local_data_contract.v61.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report = materialize(Path(args.contract), args.root, args.create)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
