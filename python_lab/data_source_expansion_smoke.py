#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v571_v590_data_source_expansion.json")
    args = ap.parse_args()
    root = Path(args.root)
    cfg = json.loads((root / "configs/data_source_expansion.v571_v590.json").read_text(encoding="utf-8"))
    docs = (root / "docs/data_source_expansion_v571_v590.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v571_v590_data_source_expansion.yml").read_text(encoding="utf-8")
    sources = {row["source_id"]: row for row in cfg.get("sources", [])}
    mapping = cfg.get("market_family_to_sources", {})
    checks = {
        "schema": cfg.get("schema") == "omnibet.data_source_expansion_contract.v571_v590",
        "source_count": len(sources) >= 4,
        "football_data": "football_data_csv" in sources and "odds_value" in mapping,
        "statsbomb": "statsbomb_open_data" in sources and "player_shots_sot" in mapping,
        "openfootball": "openfootball_json" in sources and "match_result" in mapping,
        "network_blocked": cfg.get("ci_downloads_allowed") is False and all(row.get("ci_network_allowed") is False for row in sources.values()),
        "priority_order": cfg.get("priority_order", [])[0] == "football_data_csv",
        "docs": "v571-v590 Data Source Expansion" in docs,
        "workflow": "data_source_expansion_smoke.py" in workflow,
    }
    report = {"ok": all(checks.values()), "schema": "omnibet.data_source_expansion_smoke.v571_v590", "acceptance": checks}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
