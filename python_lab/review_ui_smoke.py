#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect
from dashboard_data_smoke import build_dashboard_payload
from provider_identity_hardening_smoke import build_report as build_identity_report


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_payload(db: Path, source_a: Path, source_b: Path, links: Path) -> Dict[str, Any]:
    dash = build_dashboard_payload(db, source_a, source_b, links)
    ident = build_identity_report(db, source_a, source_b, links)
    event_id = dash["sections"]["events"][0]["canonical_event_id"]
    con = connect(db)
    try:
        unknown = rows(
            con,
            """
            SELECT source_provider_id, bookmaker, raw_market_name, raw_selection_name,
                   source_ref, decimal_odds
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='odds_market' AND needs_mapping=1
            ORDER BY raw_market_name, raw_selection_name
            """,
            (event_id,),
        )
        review_queue = rows(
            con,
            """
            SELECT canonical_entity_type, provider_id, provider_entity_id, raw_name,
                   normalized_name, candidate_canonical_id, confidence, reason
            FROM provider_identity_review_queue
            ORDER BY canonical_entity_type, raw_name
            """,
        )
        candidates = rows(
            con,
            """
            SELECT canonical_entity_type, canonical_id, provider_id, raw_name,
                   match_strategy, confidence, decision, reason
            FROM provider_identity_candidates
            ORDER BY canonical_entity_type, provider_id, raw_name
            LIMIT 30
            """,
        )
    finally:
        con.close()
    return {
        "ok": True,
        "version": "omnibet.review.v53_v54",
        "canonical_event_id": event_id,
        "sections": {
            "unknown_market_review": [
                {
                    "review_id": f"unknown:{i:03d}",
                    "provider_id": r.get("source_provider_id"),
                    "source_name": r.get("bookmaker"),
                    "raw_name": r.get("raw_market_name"),
                    "raw_selection": r.get("raw_selection_name"),
                    "source_ref": r.get("source_ref"),
                    "price": r.get("decimal_odds"),
                    "candidate_id": None,
                    "confidence": 0.0,
                    "decision": "needs_review",
                    "reason": "No exact high-confidence alias exists yet."
                }
                for i, r in enumerate(unknown)
            ],
            "provider_identity_review": {
                "review_queue": [dict(r, decision="needs_review") for r in review_queue],
                "candidate_preview": candidates,
                "identity_report_ok": ident.get("ok"),
            },
        },
        "safety": {
            "offline_only": True,
            "no_keys": True,
            "no_network": True,
            "local_actions_only": True,
            "no_persistence_yet": True,
        },
    }


def build_report(root: Path, db: Path, source_a: Path, source_b: Path, links: Path, review_out: Path) -> Dict[str, Any]:
    payload = build_payload(db, source_a, source_b, links)
    write_json(review_out, payload)
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    api = (root / "tauri-app/src/api.js").read_text(encoding="utf-8")
    app = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    review_js = (root / "tauri-app/src/review.js").read_text(encoding="utf-8")
    rust = (root / "tauri-app/src-tauri/src/main.rs").read_text(encoding="utf-8")
    sample = json.loads((root / "tauri-app/src/review-data.sample.json").read_text(encoding="utf-8"))
    sections = payload["sections"]
    markers = ["review-unknown-markets", "review-identity-candidates", "load-review-report", "load-review-sample"]
    checks = {
        "payload_ok": payload.get("ok") is True,
        "unknown_rows": len(sections["unknown_market_review"]) >= 1,
        "identity_review_rows": len(sections["provider_identity_review"]["review_queue"]) >= 1,
        "identity_candidates": len(sections["provider_identity_review"]["candidate_preview"]) >= 10,
        "review_out_written": review_out.exists(),
        "sample_ok": sample.get("ok") is True,
        "markers_in_html": all(m in html for m in markers),
        "module_linked": 'src="review.js"' in html,
        "api_command": "load_review_report" in api,
        "app_bindings": "loadAndRenderReviews" in app and "load-review-report" in app,
        "local_actions": "applyLocalReviewAction" in review_js and "review-action" in review_js,
        "tauri_command": "fn load_review_report" in rust and "load_review_report" in rust and "generate_handler!" in rust,
        "allowlisted_paths": "v53_v54_review_data.json" in rust and "review-data.sample.json" in rust,
        "paper_only": "PAPER_ONLY" in html,
        "no_network": payload["safety"]["no_network"],
    }
    return {
        "ok": all(checks.values()),
        "milestone": "v53_v54_review_ui",
        "review_out": str(review_out),
        "counts": {
            "unknown": len(sections["unknown_market_review"]),
            "identity_review": len(sections["provider_identity_review"]["review_queue"]),
            "identity_candidates": len(sections["provider_identity_review"]["candidate_preview"]),
        },
        "acceptance": checks,
        "safety": payload["safety"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--db", default="build/omnibet_v53_v54_review.sqlite")
    ap.add_argument("--source-a", default="data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--source-b", default="data/samples/api_football_live_state_sample.json")
    ap.add_argument("--links", default="data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--review-out", default="build/v53_v54_review_data.json")
    ap.add_argument("--out", default="reports/ci_v53_v54_review_ui.json")
    args = ap.parse_args()
    root = Path(args.root)
    report = build_report(root, root / args.db, root / args.source_a, root / args.source_b, root / args.links, root / args.review_out)
    write_json(root / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
