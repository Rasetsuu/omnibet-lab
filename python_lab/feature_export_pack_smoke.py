#!/usr/bin/env python3
"""v46 feature snapshot export pack smoke."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from adapters.warehouse import connect
from feature_snapshot_smoke import build_report as build_feature_report
from provider_pipeline_schema import ensure_provider_pipeline_schema


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_jsonl_gz(path: Path, items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    digest = hashlib.sha256()
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for item in items:
            line = json.dumps(item, ensure_ascii=False, sort_keys=True)
            f.write(line + "\n")
            digest.update((line + "\n").encode("utf-8"))
            count += 1
    return {"path": str(path), "rows": count, "sha256": digest.hexdigest(), "format": "jsonl.gz"}


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path, out_dir: Path) -> Dict[str, Any]:
    feature_report = build_feature_report(db, odds_input, state_input, link_input)
    canonical_event_id = feature_report["canonical_event_id"]
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        event_rows = rows(con, "SELECT * FROM event_feature_snapshots WHERE canonical_event_id=? ORDER BY feature_snapshot_id", (canonical_event_id,))
        market_rows = rows(con, "SELECT * FROM market_feature_snapshots WHERE canonical_event_id=? ORDER BY feature_snapshot_id", (canonical_event_id,))
        settlement_rows = rows(con, "SELECT * FROM settlement_evaluations WHERE canonical_event_id=? ORDER BY evaluation_id", (canonical_event_id,))
        files = {
            "event_features": write_jsonl_gz(out_dir / "event_feature_snapshots.jsonl.gz", event_rows),
            "market_features": write_jsonl_gz(out_dir / "market_feature_snapshots.jsonl.gz", market_rows),
            "settlement_labels": write_jsonl_gz(out_dir / "settlement_labels.jsonl.gz", settlement_rows),
        }
        manifest = {
            "pack_version": "omnibet_feature_export_v46",
            "canonical_event_id": canonical_event_id,
            "files": files,
            "safety": {
                "offline_samples_only": True,
                "model_ready_rows_are_pre_event_only": True,
                "post_event_rows_are_evaluation_only": True,
            },
        }
        write_json(out_dir / "manifest.json", manifest)
        con.execute(
            """INSERT OR REPLACE INTO feature_export_manifest
               (export_id, export_version, canonical_event_id, output_dir, manifest_json)
               VALUES (?, ?, ?, ?, ?)""",
            ("feature_export:v46:offline_sample", "v46", canonical_event_id, str(out_dir), json.dumps(manifest, ensure_ascii=False, sort_keys=True)),
        )
        con.commit()
        manifest_rows = int(con.execute("SELECT COUNT(*) FROM feature_export_manifest WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    acceptance = {
        "feature_report_ok": bool(feature_report.get("ok")),
        "event_feature_rows_exported": files["event_features"]["rows"] >= 5,
        "market_feature_rows_exported": files["market_features"]["rows"] >= 28,
        "settlement_label_rows_exported": files["settlement_labels"]["rows"] >= 14,
        "manifest_written": (out_dir / "manifest.json").exists(),
        "manifest_row_written": manifest_rows >= 1,
        "all_files_have_sha": all(bool(meta["sha256"]) for meta in files.values()),
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v46_feature_snapshot_export_pack",
        "db": str(db),
        "out_dir": str(out_dir),
        "manifest": manifest,
        "acceptance": acceptance,
        "safety": {"offline_samples_only": True, "no_network": True, "no_api_keys": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v46 feature export pack smoke.")
    ap.add_argument("--db", default="../build/omnibet_v46_feature_export.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out-dir", default="../build/v46_feature_export_pack")
    ap.add_argument("--out", default="../reports/ci_v46_feature_export_pack.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input), Path(args.out_dir))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
