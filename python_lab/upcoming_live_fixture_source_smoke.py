#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def timestamp_order_ok(row: Dict[str, Any]) -> bool:
    observed = parse_utc(row.get("observed_at"))
    captured = parse_utc(row.get("captured_at"))
    return observed is not None and captured is not None and observed <= captured


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ["api_key", "apikey", "secret", "token", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/upcoming_live_fixture_source.v261.json")
    sample = read_json(root / "data/provider_fixtures/v261/upcoming_live_fixture_source.sample.json")
    docs = (root / "docs/upcoming_live_fixture_source_v261.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    phase_doc = (root / "docs/live_source_prediction_context_phase_v260_265.md").read_text(encoding="utf-8")
    rows = sample.get("normalized_rows", [])
    requests = sample.get("requests", [])
    required_fields = set(contract.get("normalized_row_fields", []))
    allowed_statuses = set(contract.get("allowed_statuses", []))
    allowed_freshness = set(contract.get("allowed_freshness", []))
    allowed_readiness = set(contract.get("allowed_prediction_readiness", []))
    acceptance = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.upcoming_live_fixture_source_contract.v261",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "ci_locked": contract.get("live_fetch_enabled_in_ci") is False and sample.get("live_fetch_enabled_in_ci") is False,
        "sample_shape": sample.get("schema") == "omnibet.upcoming_live_fixture_source_sample.v261" and len(rows) >= 4 and len(requests) >= 2,
        "scheduled_rows": any(row.get("status") == "scheduled" for row in rows),
        "live_rows": any(row.get("status") == "live" for row in rows),
        "blocked_rows": any(row.get("prediction_readiness") == "blocked" for row in rows),
        "required_fields": all(required_fields.issubset(row.keys()) for row in rows),
        "allowed_statuses": all(row.get("status") in allowed_statuses for row in rows),
        "allowed_freshness": all(row.get("freshness_status") in allowed_freshness for row in rows),
        "allowed_readiness": all(row.get("prediction_readiness") in allowed_readiness for row in rows),
        "timestamp_order": all(timestamp_order_ok(row) for row in rows),
        "availability_flags": all(isinstance(row.get(key), bool) for row in rows for key in ["lineup_available", "event_data_available", "stats_available"]),
        "readiness_explained": all(isinstance(row.get("blocker_reason"), str) and row.get("blocker_reason") and isinstance(row.get("next_action"), str) and row.get("next_action") for row in rows),
        "live_row_has_state": all((row.get("minute") is not None and row.get("home_score") is not None and row.get("away_score") is not None) for row in rows if row.get("status") == "live"),
        "requests_offline": all(req.get("network_mode") == "offline_fixture" for req in requests) and all(contract.get("request_contracts", {}).get(req.get("request_type"), {}).get("ci_network_allowed") is False for req in requests),
        "no_secrets": sample.get("credential_values_present") is False and no_secret_values(sample),
        "docs_updated": "v261 Upcoming/Live Fixture Source Contract" in docs and "observed_at <= captured_at" in docs,
        "readme_updated": "v261 upcoming/live fixture source contract" in readme,
        "phase_doc_mentions_v261": "v261" in phase_doc and "Upcoming/live fixture source contract" in phase_doc,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 9,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.upcoming_live_fixture_source_smoke.v261",
        "milestone": "v261_upcoming_live_fixture_source_contract",
        "acceptance": checks,
        "summary": {
            "rows": len(rows),
            "requests": len(requests),
            "providers": sorted({row.get("provider") for row in rows}),
            "statuses": sorted({row.get("status") for row in rows}),
            "live_rows": sum(1 for row in rows if row.get("status") == "live"),
            "scheduled_rows": sum(1 for row in rows if row.get("status") == "scheduled"),
            "blocked_rows": sum(1 for row in rows if row.get("prediction_readiness") == "blocked"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v261_upcoming_live_fixture_source.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
