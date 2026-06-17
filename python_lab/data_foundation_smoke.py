#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from league_universe_smoke import build_universe


COMP_IDS = ["eng_premier", "esp_laliga", "ger_bundesliga", "usa_mls", "bra_serie_a", "uefa_champions"]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def clamp(p: float) -> float:
    return max(0.02, min(0.98, p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 20), -20)))


def result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    idx = 0
    for comp_i, comp_id in enumerate(COMP_IDS):
        for season in range(2021, 2027):
            for round_no in range(10):
                event_id = f"{comp_id}:{season}:{round_no:02d}"
                rating_diff = ((round_no % 7) - 3) / 6.0 + (comp_i - 2) * 0.03
                form_diff = (((season + round_no) % 9) - 4) / 18.0
                rest_diff = (((round_no + comp_i) % 5) - 2) / 7.0
                signal = -0.05 + 1.05 * rating_diff + 0.70 * form_diff + 0.20 * rest_diff
                if signal > 0.58:
                    hg, ag = 3, 1
                elif signal > 0.24:
                    hg, ag = 2, 1
                elif signal > -0.05:
                    hg, ag = 1, 1
                elif signal > -0.38:
                    hg, ag = 1, 2
                else:
                    hg, ag = 0, 2
                source_row = {
                    "source_id": "source_01",
                    "competition_id": comp_id,
                    "season": season,
                    "kickoff_utc": f"{season}-{(round_no % 12) + 1:02d}-{(round_no * 2 % 26) + 1:02d}T18:00:00Z",
                    "home_name": f"{comp_id}_home_{round_no % 6}",
                    "away_name": f"{comp_id}_away_{(round_no + 2) % 6}",
                    "home_score": hg,
                    "away_score": ag,
                    "source_event_id": event_id,
                    "rating_diff": round(rating_diff, 6),
                    "form_diff": round(form_diff, 6),
                    "rest_diff": round(rest_diff, 6),
                }
                source_row["payload_sha256"] = sha_text(json.dumps(source_row, sort_keys=True))
                rows.append(source_row)
                idx += 1
    duplicate = dict(rows[5])
    duplicate["duplicate_note"] = "intentional_duplicate_for_integrity_check"
    rows.append(duplicate)
    return rows


def market_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for i, row in enumerate(results[:-1]):
        if i % 2 == 0:
            p_home = clamp(0.48 + 0.22 * float(row["rating_diff"]) + 0.12 * float(row["form_diff"]))
            p_away = clamp(0.33 - 0.14 * float(row["rating_diff"]))
            p_draw = clamp(1.0 - p_home - p_away)
            total = p_home + p_draw + p_away
            for name, p in [("home", p_home / total), ("draw", p_draw / total), ("away", p_away / total)]:
                market = {
                    "source_id": "source_02",
                    "competition_id": row["competition_id"],
                    "source_event_id": row["source_event_id"],
                    "snapshot_time_utc": row["kickoff_utc"].replace("T18:", "T12:"),
                    "market_name": "match_result",
                    "selection_name": name,
                    "decimal_price": round(1.0 / clamp(p), 4),
                    "line_value": None,
                }
                market["payload_sha256"] = sha_text(json.dumps(market, sort_keys=True))
                rows.append(market)
    return rows


def write_result_csv(path: Path, rows: List[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_id", "competition_id", "season", "kickoff_utc", "home_name", "away_name", "home_score", "away_score", "source_event_id", "rating_diff", "form_diff", "rest_diff", "payload_sha256"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    return sha_file(path)


def write_market_jsonl(path: Path, rows: List[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return sha_file(path)


def load_result_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_market_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def integrity_report(results: List[Dict[str, Any]], markets: List[Dict[str, Any]], universe: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {row["competition_id"] for row in universe["leagues"] if row["default_scope"] in {"core_train", "expanded_train"}}
    seen = set()
    duplicates = []
    unmapped = []
    missing_hashes = []
    for row in results:
        key = (row["source_id"], row["source_event_id"])
        if key in seen:
            duplicates.append({"source_id": row["source_id"], "source_event_id": row["source_event_id"]})
        seen.add(key)
        if row["competition_id"] not in allowed:
            unmapped.append(row["competition_id"])
        if not row.get("payload_sha256"):
            missing_hashes.append(row["source_event_id"])
    market_events = {m["source_event_id"] for m in markets}
    result_events = {r["source_event_id"] for r in results}
    return {
        "schema": "omnibet.import_integrity.v91",
        "result_rows": len(results),
        "market_rows": len(markets),
        "unique_result_events": len(result_events),
        "market_linked_events": len(result_events & market_events),
        "duplicate_rows": duplicates,
        "unmapped_competitions": sorted(set(unmapped)),
        "missing_hash_rows": missing_hashes,
        "ok": len(unmapped) == 0 and len(missing_hashes) == 0 and len(duplicates) >= 1,
    }


def training_rows(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    seen = set()
    for row in results:
        key = (row["source_id"], row["source_event_id"])
        if key in seen:
            continue
        seen.add(key)
        hg, ag = int(row["home_score"]), int(row["away_score"])
        rows.append({
            "source_event_id": row["source_event_id"],
            "competition_id": row["competition_id"],
            "season": int(row["season"]),
            "kickoff_utc": row["kickoff_utc"],
            "rating_diff": float(row["rating_diff"]),
            "form_diff": float(row["form_diff"]),
            "rest_diff": float(row["rest_diff"]),
            "label_home_win": int(hg > ag),
            "label_draw": int(hg == ag),
            "label_away_win": int(hg < ag),
            "model_eligible": 1,
            "cutoff_policy": "pre_event_features_only",
        })
    return rows


def evaluate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    eval_rows = []
    for test_season in range(2024, 2027):
        train = [r for r in rows if r["season"] < test_season]
        test = [r for r in rows if r["season"] == test_season]
        global_base = sum(r["label_home_win"] for r in train) / len(train)
        for row in test:
            comp_train = [r for r in train if r["competition_id"] == row["competition_id"]]
            comp_base = sum(r["label_home_win"] for r in comp_train) / len(comp_train) if comp_train else global_base
            z = math.log(clamp(comp_base) / (1 - clamp(comp_base))) + 0.95 * row["rating_diff"] + 0.55 * row["form_diff"] + 0.18 * row["rest_diff"]
            p = clamp(sigmoid(z))
            eval_rows.append({"competition_id": row["competition_id"], "season": row["season"], "source_event_id": row["source_event_id"], "label_home_win": row["label_home_win"], "probability": p})
    by_comp = []
    for comp_id in sorted({r["competition_id"] for r in eval_rows}):
        part = [r for r in eval_rows if r["competition_id"] == comp_id]
        brier = sum((r["probability"] - r["label_home_win"]) ** 2 for r in part) / len(part)
        acc = sum((r["probability"] >= 0.5) == bool(r["label_home_win"]) for r in part) / len(part)
        by_comp.append({"competition_id": comp_id, "rows": len(part), "brier": round(brier, 6), "accuracy_at_0_5": round(acc, 6)})
    return {"schema": "omnibet.imported_eval.v93", "rows": eval_rows, "per_competition": by_comp}


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return sha_file(path)


def build(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    universe = build_universe()
    result_sample = result_rows()
    market_sample = market_rows(result_sample)
    paths = {
        "result_csv": out_dir / "local_results_sample.v88.csv",
        "market_jsonl": out_dir / "local_market_snapshot_sample.v89.jsonl",
        "integrity": out_dir / "import_integrity.v91.json",
        "training": out_dir / "imported_training_rows.v92.jsonl",
        "evaluation": out_dir / "imported_per_competition_eval.v93.json",
        "desktop": out_dir / "adapter_readiness_payload.v94.json",
    }
    result_sha = write_result_csv(paths["result_csv"], result_sample)
    market_sha = write_market_jsonl(paths["market_jsonl"], market_sample)
    loaded_results = load_result_csv(paths["result_csv"])
    loaded_markets = load_market_jsonl(paths["market_jsonl"])
    integrity = integrity_report(loaded_results, loaded_markets, universe)
    train = training_rows(loaded_results)
    eval_report = evaluate(train)
    write_json(paths["integrity"], integrity)
    training_sha = write_jsonl(paths["training"], train)
    write_json(paths["evaluation"], eval_report)
    coverage = {
        "schema": "omnibet.competition_coverage.v90",
        "covered_competitions": sorted({r["competition_id"] for r in loaded_results}),
        "covered_count": len({r["competition_id"] for r in loaded_results}),
        "trainable_universe_count": universe["row_counts"]["trainable"],
        "coverage_ratio": round(len({r["competition_id"] for r in loaded_results}) / universe["row_counts"]["trainable"], 6),
    }
    desktop = {
        "ok": True,
        "schema": "omnibet.adapter_readiness_payload.v94",
        "coverage": coverage,
        "integrity": integrity,
        "training_rows": len(train),
        "evaluation_rows": len(eval_report["rows"]),
        "per_competition_eval": eval_report["per_competition"],
        "sample_files": {k: str(v) for k, v in paths.items()},
        "policy": {"offline_only": True, "no_website_automation": True, "local_files_only": True},
    }
    write_json(paths["desktop"], desktop)
    manifest = {
        "ok": True,
        "schema": "omnibet.data_foundation_manifest.v87_v94",
        "milestones": {"v87": "local input contracts", "v88": "result-row sample", "v89": "market-row sample", "v90": "competition coverage", "v91": "integrity and dedupe", "v92": "imported training rows", "v93": "imported per-competition evaluation", "v94": "desktop readiness payload"},
        "outputs": {k: str(v) for k, v in paths.items()},
        "hashes": {"result_csv_sha256": result_sha, "market_jsonl_sha256": market_sha, "training_sha256": training_sha, **{f"{k}_sha256": sha_file(v) for k, v in paths.items() if v.exists()}},
        "row_counts": {"result_rows": len(loaded_results), "market_rows": len(loaded_markets), "training_rows": len(train), "evaluation_rows": len(eval_report["rows"]), "covered_competitions": coverage["covered_count"]},
        "policy": desktop["policy"],
    }
    manifest_path = out_dir / "data_foundation_manifest.v87_v94.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "manifest_path": manifest_path, "desktop": desktop}


def build_report(out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    built = build(out_dir)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.adapter_readiness.sample.v94", "manifest": built["manifest"], "adapter_readiness": built["desktop"]})
    m = built["manifest"]
    checks = {
        "result_rows_present": m["row_counts"]["result_rows"] >= 300,
        "market_rows_present": m["row_counts"]["market_rows"] >= 300,
        "training_rows_present": m["row_counts"]["training_rows"] >= 300,
        "evaluation_rows_present": m["row_counts"]["evaluation_rows"] >= 100,
        "competition_coverage": m["row_counts"]["covered_competitions"] >= 3,
        "hashes_present": all(m["hashes"].values()),
        "ui_sample_written": ui_sample is not None and ui_sample.exists(),
        "offline_only": m["policy"]["offline_only"] is True,
        "local_files_only": m["policy"]["local_files_only"] is True,
    }
    return {"ok": all(checks.values()), "milestone": "v87_v94_data_foundation", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": m}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="build/data_foundation_v87_v94")
    ap.add_argument("--ui-sample", default="tauri-app/src/adapter-readiness.sample.json")
    ap.add_argument("--out", default="reports/ci_v87_v94_data_foundation.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
