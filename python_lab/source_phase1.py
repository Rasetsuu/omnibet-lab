#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

SOURCES = [
    {"source_id": "source_a", "label": "market source sample", "credential_env": "SOURCE_A_TOKEN", "parts": ["data", "samples", "the_odds_api_event_markets_sample.json"], "kind": "event_markets"},
    {"source_id": "source_b", "label": "match-state source sample", "credential_env": "SOURCE_B_TOKEN", "parts": ["data", "samples", "api_football_live_state_sample.json"], "kind": "fixture_state"},
]


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def status(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    env = env if env is not None else os.environ
    rows = []
    for src in SOURCES:
        rows.append({
            "source_id": src["source_id"],
            "label": src["label"],
            "enabled": False,
            "credential_env": src["credential_env"],
            "credential_status_only": "present" if env.get(src["credential_env"]) else "missing",
            "credential_value_displayed": False,
            "manual_action_only": True,
            "background_action_enabled": False,
            "ci_external_calls": False,
        })
    return {"ok": True, "schema": "omnibet.source_status.v63", "sources": rows, "safety": {"disabled_by_default": True, "credential_values_displayed": False, "manual_only": True, "ci_external_calls": False}}


def source_by_id(source_id: str) -> Dict[str, Any] | None:
    return next((s for s in SOURCES if s["source_id"] == source_id), None)


def cache_sample(root: Path, source_id: str, repo_root: Path) -> Dict[str, Any]:
    src = source_by_id(source_id)
    if src is None:
        return {"ok": False, "source_id": source_id, "error": "unknown source"}
    sample = repo_root.joinpath(*src["parts"])
    if not sample.exists():
        return {"ok": False, "source_id": source_id, "error": "sample missing"}
    text = sample.read_text(encoding="utf-8")
    out_dir = root / "cache" / "source_snapshots" / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_path = out_dir / f"{src['kind']}.sample.json"
    manifest_path = out_dir / "snapshot_manifest.json"
    payload_path.write_text(text, encoding="utf-8")
    manifest = {
        "ok": True,
        "schema": "omnibet.cached_source_snapshot.v65",
        "source_id": source_id,
        "snapshot_kind": src["kind"],
        "source_mode": "offline_sample_cache",
        "manual_action_required": True,
        "external_call_performed": False,
        "payload_path": str(payload_path),
        "payload_sha256": sha_text(text),
        "created_at_unix": int(time.time()),
        "safety": {"credential_value_stored": False, "external_call": False, "ci_safe": True},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "source_id": source_id, "manifest_path": str(manifest_path), "payload_path": str(payload_path), "manifest_sha256": sha_file(manifest_path)}


def cache_all(root: Path, repo_root: Path) -> Dict[str, Any]:
    results = [cache_sample(root, s["source_id"], repo_root) for s in SOURCES]
    index_path = root / "cache" / "source_snapshots" / "cache_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"ok": all(r.get("ok") for r in results), "schema": "omnibet.source_snapshot_cache_index.v65", "results": results, "safety": {"credential_values_stored": False, "external_calls": False, "ci_safe": True}}
    index_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**report, "index_path": str(index_path), "index_sha256": sha_file(index_path)}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def candidate(record: Dict[str, Any]) -> Dict[str, Any] | None:
    if record.get("decision") != "accepted":
        return None
    kind = record.get("review_type")
    if kind not in {"unknown_market", "provider_identity"}:
        return None
    return {"candidate_kind": f"{kind}_mapping_candidate", "review_id": record.get("review_id"), "candidate_status": "candidate_only_not_production", "source_decision": "accepted", "reason": record.get("reason", "accepted local review")}


def promote(decision_store: Path, output_path: Path) -> Dict[str, Any]:
    records = read_jsonl(decision_store)
    candidates = [c for c in (candidate(r) for r in records) if c is not None]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"ok": True, "schema": "omnibet.review_promotion.v66", "input_rows": len(records), "candidate_rows": len(candidates), "production_rows_written": 0, "candidates": candidates, "safety": {"candidate_only": True, "production_mapping_mutated": False, "credential_values_included": False, "external_calls": False}}
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**report, "output_path": str(output_path), "output_sha256": sha_file(output_path)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".omnibet-local")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--cache-samples", action="store_true")
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--decision-store", default=None)
    ap.add_argument("--promotion-out", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    if args.status:
        report = status()
    elif args.cache_samples:
        report = cache_sample(root, args.source_id, Path(args.repo_root)) if args.source_id else cache_all(root, Path(args.repo_root))
    elif args.promote:
        store = Path(args.decision_store) if args.decision_store else root / "review_decisions" / "review_decisions.jsonl"
        out = Path(args.promotion_out) if args.promotion_out else root / "exports" / "mapping_rule_candidates.v66.json"
        report = promote(store, out)
    else:
        report = {"ok": True, "catalog": SOURCES, "status": status()}
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(text)
    if not report.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
