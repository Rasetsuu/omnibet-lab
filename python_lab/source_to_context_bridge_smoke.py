#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def has(text: str, needle: str) -> bool:
    return needle in text


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def order_ok(row: Dict[str, Any], left_key: str = "observed_at", right_key: str = "captured_at") -> bool:
    left = parse_utc(row.get(left_key))
    right = parse_utc(row.get(right_key))
    return left is not None and right is not None and left <= right


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ["api_key", "apikey", "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def ids_unique(text: str) -> bool:
    ids = html_ids(text)
    return len(ids) == len(set(ids))


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/source_to_context_bridge.v262_v265.json")
    sample = read_json(root / "data/provider_fixtures/v262_v265/source_to_context_bridge.sample.json")
    desktop_sample = read_json(root / "tauri-app/src/live-source.sample.json")
    docs = (root / "docs/source_to_context_bridge_v262_v265.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    index = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    live_js = (root / "tauri-app/src/live_source.js").read_text(encoding="utf-8")

    fixture_rows = sample.get("fixture_rows", [])
    odds_rows = sample.get("odds_snapshot_rows", [])
    snapshots = sample.get("live_snapshot_rows", [])
    contexts = sample.get("prediction_context_bundles", [])
    acceptance = contract.get("acceptance", {})
    fixture_ids = {row.get("canonical_fixture_id") for row in fixture_rows}

    odds_fields = set(contract.get("v262_odds_snapshot_required_fields", []))
    snapshot_fields = set(contract.get("v264_snapshot_required_fields", []))
    context_fields = set(contract.get("v265_context_required_fields", []))
    panel_ids = contract.get("v263_desktop_panel_ids", [])
    button_ids = contract.get("v263_button_ids", [])
    allowed_snapshot_types = set(contract.get("allowed_snapshot_types", []))
    allowed_retention_tiers = set(contract.get("allowed_retention_tiers", []))
    allowed_readiness = set(contract.get("allowed_prediction_readiness", []))
    allowed_market_statuses = set(contract.get("allowed_market_statuses", []))
    allowed_odds_freshness = set(contract.get("allowed_odds_freshness", []))

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_to_context_bridge_contract.v262_v265",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "ci_locked": contract.get("live_fetch_enabled_in_ci") is False and sample.get("live_fetch_enabled_in_ci") is False,
        "sample_shape": sample.get("schema") == "omnibet.source_to_context_bridge_sample.v262_v265" and len(fixture_rows) >= 2 and len(odds_rows) >= 4 and len(snapshots) >= 3 and len(contexts) >= 2,
        "v262_odds_required_fields": all(odds_fields.issubset(row.keys()) for row in odds_rows),
        "v262_odds_join_fixture_rows": all(row.get("canonical_fixture_id") in fixture_ids for row in odds_rows),
        "v262_odds_enums": all(row.get("market_status") in allowed_market_statuses and row.get("freshness_status") in allowed_odds_freshness for row in odds_rows),
        "v262_odds_timestamps": all(order_ok(row) for row in odds_rows),
        "v262_missing_odds_explicit": any(row.get("market_status") == "missing" and row.get("missing_reason") not in (None, "", "none") for row in odds_rows),
        "v263_desktop_sample": desktop_sample.get("schema") == "omnibet.live_source_desktop_sample.v263_v265" and desktop_sample.get("paper_only") is True and len(desktop_sample.get("matches", [])) >= 2,
        "v263_desktop_panel_wired": has(index, 'data-page="live-source"') and all(panel_id in index for panel_id in panel_ids) and all(button_id in index for button_id in button_ids) and 'src="live_source.js"' in index,
        "v263_app_binding": contains_all(app, ["./live_source.js", "loadAndRenderLiveSourceBridge", "load-live-source-bridge"]),
        "v263_renderer": contains_all(live_js, ["renderLiveSourceBridge", "renderMatches", "renderOdds", "renderContext", "paper_watch_only"]),
        "v263_html_ids_unique": ids_unique(index),
        "v264_snapshot_required_fields": all(snapshot_fields.issubset(row.keys()) for row in snapshots),
        "v264_snapshot_enums": all(row.get("snapshot_type") in allowed_snapshot_types and row.get("retention_tier") in allowed_retention_tiers for row in snapshots),
        "v264_snapshot_timestamps": all(order_ok(row) for row in snapshots),
        "v264_retention_policy": any(row.get("delete_raw_after_promotion") is True for row in snapshots) and any(row.get("snapshot_type") == "post_match_settlement" and row.get("delete_raw_after_promotion") is False for row in snapshots),
        "v264_settlement_separate": any(row.get("snapshot_type") == "post_match_settlement" and "settlement" in row.get("promotion_state", "") for row in snapshots),
        "v265_context_required_fields": all(context_fields.issubset(row.keys()) for row in contexts),
        "v265_context_join_fixture_rows": all(row.get("canonical_fixture_id") in fixture_ids for row in contexts),
        "v265_context_timestamps": all(parse_utc(row.get("prediction_time")) is not None for row in contexts),
        "v265_context_readiness": all(row.get("prediction_readiness") in allowed_readiness for row in contexts),
        "v265_trust_blockers_explicit": all(isinstance(row.get("trust_blockers"), list) and row.get("trust_blockers") for row in contexts),
        "v265_allowed_actions_safe": all(set(row.get("allowed_actions", [])).issubset({"inspect_context", "paper_watch_only"}) for row in contexts),
        "no_secret_values": sample.get("credential_values_present") is False and no_secret_values(sample) and no_secret_values(desktop_sample),
        "paper_only_no_recommendations": sample.get("paper_only") is True and desktop_sample.get("paper_only") is True and "recommendation" not in json.dumps(sample).lower(),
        "docs_updated": "v262-v265 Source-to-Context Bridge" in docs and "observed_at <= captured_at" in docs,
        "readme_updated": "v262-v265 source-to-context bridge" in readme,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_to_context_bridge_smoke.v262_v265",
        "milestone": "v262_v265_source_to_context_bridge",
        "acceptance": checks,
        "summary": {
            "fixture_rows": len(fixture_rows),
            "odds_rows": len(odds_rows),
            "snapshot_rows": len(snapshots),
            "context_bundles": len(contexts),
            "desktop_matches": len(desktop_sample.get("matches", [])),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v262_v265_source_to_context_bridge.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
