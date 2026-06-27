#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = [
        '"api_key":',
        '"secret":',
        '"bearer_token":',
        '"credential_value":',
        "secret_value",
        "bearer ",
        "sk-",
    ]
    return not any(marker in serialized for marker in forbidden)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def readme_mentions_market_terminal(readme: str) -> bool:
    lowered = readme.lower()
    return "v291-v300" in lowered and "market terminal" in lowered and "mvp" in lowered


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/market_terminal_mvp.v291_v300.json")
    sample = read_json(root / "tauri-app/src/market-terminal.sample.json")
    docs = (root / "docs/market_terminal_mvp_v291_v300.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/market_terminal_v291.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v291_v300_market_terminal_mvp.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/market_terminal.js").read_text(encoding="utf-8")

    fixtures = sample.get("fixtures", [])
    predictions = sample.get("prediction_rows", [])
    watchlist = sample.get("paper_watchlist", [])
    ledger = sample.get("paper_ledger_preview", [])
    bilet = sample.get("bilet_builder_placeholder", {})
    acceptance = contract.get("acceptance", {})
    ids = html_ids(html)

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.market_terminal_mvp_contract.v291_v300",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "no_live_calls_credentials_recommendations": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and sample.get("credential_values_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "sample_shape": sample.get("schema") == "omnibet.market_terminal_mvp_sample.v291_v300" and len(fixtures) >= 2 and len(predictions) >= 3 and len(watchlist) >= 1 and len(ledger) >= 1,
        "fixture_rows_required": all(required_subset(contract.get("fixture_row_required_fields", []), row) for row in fixtures),
        "prediction_rows_required": all(required_subset(contract.get("prediction_row_required_fields", []), row) for row in predictions),
        "watchlist_rows_required": all(required_subset(contract.get("watchlist_required_fields", []), row) for row in watchlist),
        "ledger_rows_required": all(required_subset(contract.get("ledger_preview_required_fields", []), row) for row in ledger),
        "allowed_actions_safe": set(contract.get("allowed_actions", [])).issubset({"inspect", "paper_watch_only"}) and all(row.get("allowed_action") in {"inspect", "paper_watch_only"} for row in predictions),
        "forbidden_actions_present": {"recommend_real_bet", "place_bet", "auto_stake", "claim_profitability", "enable_bilet_builder_real_mode"}.issubset(set(contract.get("forbidden_actions", []))),
        "trust_statuses_defined": {"unsupported", "sample_only", "paper_watch", "validated_paper"}.issubset(set(contract.get("trust_statuses", []))),
        "bilet_builder_disabled": bilet.get("enabled") is False and bilet.get("minimum_required_trust_status") == "validated_paper" and contract.get("minimum_bilet_builder_status") == "validated_paper",
        "ledger_forbids_real_stake": all(row.get("real_stake_allowed") is False for row in ledger),
        "freshness_badges": {"fresh_sample", "stale_sample", "missing_timestamp", "offline_sample"}.issubset(set(contract.get("source_freshness_badges", []))) and all(row.get("source_freshness") in contract.get("source_freshness_badges", []) for row in fixtures),
        "html_page_wired": 'data-page="market-terminal"' in html and all(panel_id in html for panel_id in contract.get("panel_ids", [])) and all(button_id in html for button_id in contract.get("button_ids", [])) and 'src="market_terminal.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./market_terminal.js" in app_js and "loadAndRenderMarketTerminalMvp" in app_js and "load-market-terminal-mvp" in app_js,
        "renderer_wired": "renderMarketTerminalMvp" in renderer and "renderPredictions" in renderer and "renderBiletBuilder" in renderer and "allowed_action" in renderer,
        "rust_module_exposed": "pub mod market_terminal_v291;" in rust_lib and "pub use market_terminal_v291::*;" in rust_lib,
        "rust_module_validation": "validate_market_terminal_mvp_contract" in rust_module and "recommend_real_bet" in rust_module and "validated_paper" in rust_module,
        "docs_updated": "v291-v300 Market Terminal MVP" in docs and "bilet builder" in docs.lower(),
        "readme_updated": readme_mentions_market_terminal(readme),
        "workflow_updated": "market_terminal_mvp_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.market_terminal_mvp_smoke.v291_v300",
        "milestone": "v291_v300_market_terminal_mvp",
        "acceptance": checks,
        "summary": {
            "fixtures": len(fixtures),
            "prediction_rows": len(predictions),
            "watchlist_rows": len(watchlist),
            "ledger_rows": len(ledger),
            "bilet_builder_enabled": bilet.get("enabled"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v291_v300_market_terminal_mvp.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
