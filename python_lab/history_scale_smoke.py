#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List

from league_universe_smoke import build_universe


CSV_COMPS = ["eng_premier", "esp_laliga", "ita_serie_a", "ger_bundesliga", "fra_ligue1", "por_primeira", "ned_eredivisie", "usa_mls"]
JSON_COMPS = ["bra_serie_a", "arg_primera", "mex_liga_mx", "jpn_j1", "uefa_champions", "uefa_europa"]


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


def make_row(comp_id: str, season: int, round_no: int, source_id: str, comp_offset: int) -> Dict[str, Any]:
    rating_diff = ((round_no % 9) - 4) / 7.0 + (comp_offset % 5 - 2) * 0.025
    form_diff = (((season + round_no + comp_offset) % 11) - 5) / 22.0
    rest_diff = (((round_no + comp_offset) % 7) - 3) / 7.0
    signal = -0.06 + 1.0 * rating_diff + 0.74 * form_diff + 0.18 * rest_diff
    if signal > 0.62:
        hg, ag = 3, 1
    elif signal > 0.28:
        hg, ag = 2, 1
    elif signal > -0.05:
        hg, ag = 1, 1
    elif signal > -0.38:
        hg, ag = 1, 2
    else:
        hg, ag = 0, 2
    row = {
        "source_id": source_id,
        "competition_id": comp_id,
        "season": season,
        "round_no": round_no,
        "kickoff_utc": f"{season}-{(round_no % 12) + 1:02d}-{(round_no * 2 % 26) + 1:02d}T18:00:00Z",
        "home_name": f"{comp_id}_home_{round_no % 10}",
        "away_name": f"{comp_id}_away_{(round_no + 3) % 10}",
        "home_score": hg,
        "away_score": ag,
        "source_event_id": f"{comp_id}:{season}:{round_no:03d}",
        "rating_diff": round(rating_diff, 6),
        "form_diff": round(form_diff, 6),
        "rest_diff": round(rest_diff, 6),
    }
    row["payload_sha256"] = sha_text(json.dumps(row, sort_keys=True))
    return row


def csv_rows() -> List[Dict[str, Any]]:
    rows = []
    for ci, comp in enumerate(CSV_COMPS):
        for season in range(2016, 2027):
            for round_no in range(22):
                rows.append(make_row(comp, season, round_no, "source_csv", ci))
    rows.append(dict(rows[7]))
    return rows


def json_rows() -> List[Dict[str, Any]]:
    rows = []
    for ci, comp in enumerate(JSON_COMPS, start=20):
        for season in range(2017, 2027):
            for round_no in range(18):
                base = make_row(comp, season, round_no, "source_json", ci)
                base["event_detail"] = {"home_xg_proxy": round(1.0 + max(base["rating_diff"], -0.4), 4), "away_xg_proxy": round(1.0 - min(base["rating_diff"], 0.4), 4)}
                base["payload_sha256"] = sha_text(json.dumps(base, sort_keys=True))
                rows.append(base)
    rows.append(dict(rows[11]))
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_id", "competition_id", "season", "round_no", "kickoff_utc", "home_name", "away_name", "home_score", "away_score", "source_event_id", "rating_diff", "form_diff", "rest_diff", "payload_sha256"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    return sha_file(path)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return sha_file(path)


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                if "event_detail" in row:
                    row["home_xg_proxy"] = row["event_detail"].get("home_xg_proxy")
                    row["away_xg_proxy"] = row["event_detail"].get("away_xg_proxy")
                rows.append(row)
    return rows


def normalize(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "source_id": row["source_id"],
            "competition_id": row["competition_id"],
            "season": int(row["season"]),
            "round_no": int(row["round_no"]),
            "kickoff_utc": row["kickoff_utc"],
            "home_name": row["home_name"],
            "away_name": row["away_name"],
            "home_score": int(row["home_score"]),
            "away_score": int(row["away_score"]),
            "source_event_id": row["source_event_id"],
            "rating_diff": float(row["rating_diff"]),
            "form_diff": float(row["form_diff"]),
            "rest_diff": float(row["rest_diff"]),
            "home_xg_proxy": float(row.get("home_xg_proxy") or 0.0),
            "away_xg_proxy": float(row.get("away_xg_proxy") or 0.0),
            "payload_sha256": row["payload_sha256"],
        })
    return out


def dedupe(rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    seen = set()
    out = []
    dupes = []
    for row in rows:
        key = (row["source_id"], row["source_event_id"])
        if key in seen:
            dupes.append({"source_id": row["source_id"], "source_event_id": row["source_event_id"]})
            continue
        seen.add(key)
        out.append(row)
    return out, dupes


def coverage(rows: List[Dict[str, Any]], universe: Dict[str, Any]) -> Dict[str, Any]:
    trainable = {r["competition_id"] for r in universe["leagues"] if r["default_scope"] in {"core_train", "expanded_train"}}
    comp_ids = sorted({r["competition_id"] for r in rows})
    seasons_by_comp = {comp: sorted({r["season"] for r in rows if r["competition_id"] == comp}) for comp in comp_ids}
    return {
        "schema": "omnibet.history_coverage.v100",
        "covered_competitions": comp_ids,
        "covered_count": len(comp_ids),
        "trainable_universe_count": len(trainable),
        "coverage_ratio": round(len(comp_ids) / len(trainable), 6),
        "seasons_by_competition": seasons_by_comp,
        "min_seasons": min(len(v) for v in seasons_by_comp.values()),
        "max_seasons": max(len(v) for v in seasons_by_comp.values()),
    }


def training_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        hg, ag = row["home_score"], row["away_score"]
        out.append({
            "source_event_id": row["source_event_id"],
            "competition_id": row["competition_id"],
            "season": row["season"],
            "rating_diff": row["rating_diff"],
            "form_diff": row["form_diff"],
            "rest_diff": row["rest_diff"],
            "xg_proxy_diff": row["home_xg_proxy"] - row["away_xg_proxy"],
            "label_home_win": int(hg > ag),
            "model_eligible": 1,
        })
    return out


def evaluate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    preds = []
    for test_season in range(2024, 2027):
        train = [r for r in rows if r["season"] < test_season]
        test = [r for r in rows if r["season"] == test_season]
        global_base = sum(r["label_home_win"] for r in train) / len(train)
        for row in test:
            comp_train = [r for r in train if r["competition_id"] == row["competition_id"]]
            comp_base = sum(r["label_home_win"] for r in comp_train) / len(comp_train) if comp_train else global_base
            z = math.log(clamp(comp_base) / (1 - clamp(comp_base))) + 0.86 * row["rating_diff"] + 0.58 * row["form_diff"] + 0.18 * row["rest_diff"] + 0.12 * row["xg_proxy_diff"]
            p = clamp(sigmoid(z))
            preds.append({"competition_id": row["competition_id"], "season": row["season"], "source_event_id": row["source_event_id"], "label_home_win": row["label_home_win"], "probability": p})
    per_comp = []
    for comp in sorted({p["competition_id"] for p in preds}):
        part = [p for p in preds if p["competition_id"] == comp]
        brier = sum((p["probability"] - p["label_home_win"]) ** 2 for p in part) / len(part)
        acc = sum((p["probability"] >= 0.5) == bool(p["label_home_win"]) for p in part) / len(part)
        per_comp.append({"competition_id": comp, "rows": len(part), "brier": round(brier, 6), "accuracy_at_0_5": round(acc, 6)})
    return {"schema": "omnibet.history_eval.v102", "rows": preds, "per_competition": per_comp}


def build(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    universe = build_universe()
    csv_sample = csv_rows()
    json_sample = json_rows()
    paths = {
        "registry": out_dir / "source_file_registry.v95.json",
        "csv": out_dir / "season_rows.v96.csv",
        "jsonl": out_dir / "json_rows.v97_v98.jsonl",
        "normalized": out_dir / "normalized_history.v99.jsonl",
        "coverage": out_dir / "coverage_payload.v100.json",
        "integrity": out_dir / "integrity_report.v101.json",
        "training": out_dir / "history_training_rows.v102.jsonl",
        "evaluation": out_dir / "history_eval.v102.json",
        "desktop": out_dir / "history_scale_payload.v102.json",
    }
    registry = {"schema": "omnibet.source_file_registry.v95", "files": [{"file_id": "season_csv", "path": str(paths["csv"]), "format": "csv"}, {"file_id": "json_rows", "path": str(paths["jsonl"]), "format": "jsonl"}]}
    write_json(paths["registry"], registry)
    csv_sha = write_csv(paths["csv"], csv_sample)
    json_sha = write_jsonl(paths["jsonl"], json_sample)
    imported = normalize(load_csv(paths["csv"]) + load_jsonl(paths["jsonl"]))
    deduped, dupes = dedupe(imported)
    normalized_sha = write_jsonl(paths["normalized"], deduped)
    cov = coverage(deduped, universe)
    integ = {"schema": "omnibet.history_integrity.v101", "input_rows": len(imported), "deduped_rows": len(deduped), "duplicate_rows": dupes, "missing_hash_rows": [r["source_event_id"] for r in deduped if not r.get("payload_sha256")], "ok": len(dupes) >= 2}
    train = training_rows(deduped)
    train_sha = write_jsonl(paths["training"], train)
    eval_report = evaluate(train)
    write_json(paths["coverage"], cov)
    write_json(paths["integrity"], integ)
    write_json(paths["evaluation"], eval_report)
    desktop = {"ok": True, "schema": "omnibet.history_scale_payload.v102", "coverage": cov, "integrity": integ, "training_rows": len(train), "evaluation_rows": len(eval_report["rows"]), "per_competition_eval": eval_report["per_competition"], "policy": {"offline_only": True, "local_files_only": True}}
    write_json(paths["desktop"], desktop)
    hashes = {f"{k}_sha256": sha_file(v) for k, v in paths.items()}
    hashes.update({"csv_input_sha256": csv_sha, "json_input_sha256": json_sha, "normalized_sha256": normalized_sha, "training_sha256": train_sha})
    manifest = {"ok": True, "schema": "omnibet.history_scale_manifest.v95_v102", "outputs": {k: str(v) for k, v in paths.items()}, "hashes": hashes, "row_counts": {"csv_rows": len(csv_sample), "json_rows": len(json_sample), "imported_rows": len(imported), "deduped_rows": len(deduped), "training_rows": len(train), "evaluation_rows": len(eval_report["rows"]), "covered_competitions": cov["covered_count"], "min_seasons": cov["min_seasons"]}, "policy": desktop["policy"]}
    manifest_path = out_dir / "history_scale_manifest.v95_v102.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "manifest_path": manifest_path, "desktop": desktop}


def build_report(out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    built = build(out_dir)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.history_scale.sample.v102", "manifest": built["manifest"], "history_scale": built["desktop"]})
    m = built["manifest"]
    checks = {"imported_rows_2000": m["row_counts"]["imported_rows"] >= 2000, "deduped_rows_2000": m["row_counts"]["deduped_rows"] >= 2000, "coverage_12": m["row_counts"]["covered_competitions"] >= 12, "seasons_6": m["row_counts"]["min_seasons"] >= 6, "training_rows_2000": m["row_counts"]["training_rows"] >= 2000, "evaluation_rows_300": m["row_counts"]["evaluation_rows"] >= 300, "hashes_present": all(m["hashes"].values()), "ui_sample_written": ui_sample is not None and ui_sample.exists(), "offline_only": m["policy"]["offline_only"] is True}
    return {"ok": all(checks.values()), "milestone": "v95_v102_history_scale", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": m}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="build/history_scale_v95_v102")
    ap.add_argument("--ui-sample", default="tauri-app/src/history-scale.sample.json")
    ap.add_argument("--out", default="reports/ci_v95_v102_history_scale.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
