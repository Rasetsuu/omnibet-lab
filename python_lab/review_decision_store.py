#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

VALID_DECISIONS = {"accepted", "rejected", "needs_review"}
VALID_REVIEW_TYPES = {"unknown_market", "provider_identity"}


def normalized_decision(value: str) -> str:
    value = value.replace("_local", "")
    if value not in VALID_DECISIONS:
        raise ValueError(f"unsupported decision: {value}")
    return value


def decision_record(review_type: str, review_id: str, decision: str, reason: str, actor: str = "local_gui") -> Dict[str, Any]:
    if review_type not in VALID_REVIEW_TYPES:
        raise ValueError(f"unsupported review_type: {review_type}")
    return {
        "schema": "omnibet.review_decision.v59",
        "review_type": review_type,
        "review_id": review_id,
        "decision": normalized_decision(decision),
        "reason": reason,
        "actor": actor,
        "created_at_unix": int(time.time()),
        "source": "desktop_local_review_ui",
    }


def append_decision(path: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {"ok": True, "path": str(path), "record": record}


def read_decisions(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def summarize(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    total = 0
    for record in records:
        total += 1
        counts[record.get("decision", "unknown")] = counts.get(record.get("decision", "unknown"), 0) + 1
        by_type[record.get("review_type", "unknown")] = by_type.get(record.get("review_type", "unknown"), 0) + 1
    return {"ok": True, "total": total, "decision_counts": counts, "type_counts": by_type}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=".omnibet-local/review_decisions/review_decisions.jsonl")
    ap.add_argument("--review-type", choices=sorted(VALID_REVIEW_TYPES))
    ap.add_argument("--review-id")
    ap.add_argument("--decision", choices=sorted(VALID_DECISIONS))
    ap.add_argument("--reason", default="local desktop review decision")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    path = Path(args.store)
    if args.summary:
        print(json.dumps(summarize(read_decisions(path)), indent=2, ensure_ascii=False))
        return
    if not args.review_type or not args.review_id or not args.decision:
        raise SystemExit("--review-type, --review-id, and --decision are required unless --summary is used")
    record = decision_record(args.review_type, args.review_id, args.decision, args.reason)
    print(json.dumps(append_decision(path, record), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
