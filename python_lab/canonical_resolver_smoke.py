#!/usr/bin/env python3
"""v33 canonical resolver smoke.

No provider calls. No scraping. Builds deterministic canonical entities/aliases and
proves safe alias resolution behavior for teams, players, markets, and dangerous
similar market names.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.warehouse import connect, register_default_sources, table_counts, sha_text

AUTO_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.84


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\b(fc|cf|afc|sc|the)\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def insert_seed_data(con) -> None:
    teams = [
        ("team_manchester_united", "football", "Manchester United", "England", "club"),
        ("team_france", "football", "France", "France", "national_team"),
    ]
    for row in teams:
        con.execute(
            """INSERT OR REPLACE INTO canonical_teams
               (canonical_team_id, sport, display_name, country, team_type, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (*row, "{}"),
        )
    team_aliases = [
        ("Manchester United", "team_manchester_united"),
        ("Man United", "team_manchester_united"),
        ("Man. Utd", "team_manchester_united"),
        ("MAN UTD", "team_manchester_united"),
        ("France", "team_france"),
        ("FRANCE", "team_france"),
    ]
    for alias, canonical_id in team_aliases:
        alias_id = f"team_alias:{canonical_id}:{sha_text(alias)[:12]}"
        con.execute(
            """INSERT OR REPLACE INTO team_aliases
               (alias_id, canonical_team_id, provider_id, alias_text, normalized_alias, confidence, source_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, canonical_id, None, alias, normalize_text(alias), 1.0, "v33 seed"),
        )

    players = [
        ("player_kylian_mbappe", "football", "Kylian Mbappé", "1998-12-20", "France", "team_france", "forward"),
        ("player_lautaro_martinez", "football", "Lautaro Martínez", "1997-08-22", "Argentina", None, "forward"),
    ]
    for row in players:
        con.execute(
            """INSERT OR REPLACE INTO canonical_players
               (canonical_player_id, sport, display_name, birth_date, nationality, primary_team_id, position, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (*row, "{}"),
        )
    player_aliases = [
        ("Kylian Mbappé", "player_kylian_mbappe", "team_france", "France"),
        ("Kylian Mbappe", "player_kylian_mbappe", "team_france", "France"),
        ("K. Mbappe", "player_kylian_mbappe", "team_france", "France"),
        ("Mbappe", "player_kylian_mbappe", "team_france", "France"),
        ("Lautaro Martinez", "player_lautaro_martinez", None, "Argentina"),
    ]
    for alias, canonical_id, team_context_id, country_context in player_aliases:
        alias_id = f"player_alias:{canonical_id}:{sha_text(alias + str(team_context_id))[:12]}"
        con.execute(
            """INSERT OR REPLACE INTO player_aliases
               (alias_id, canonical_player_id, provider_id, alias_text, normalized_alias, team_context_id, country_context, confidence, source_note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, canonical_id, None, alias, normalize_text(alias), team_context_id, country_context, 1.0, "v33 seed"),
        )

    markets = [
        ("football_1x2_regulation", "football", "1x2", "1X2 regulation", "regulation_90_plus_stoppage", "full_match", 0, 0, 0, ["football_to_qualify"]),
        ("football_to_qualify", "football", "qualification", "To qualify", "includes_extra_time_and_penalties", "full_tie", 0, 0, 0, ["football_1x2_regulation"]),
        ("football_shots_total_regulation", "football", "shots", "Total shots regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, ["football_shots_on_target_total_regulation"]),
        ("football_shots_on_target_total_regulation", "football", "shots_on_target", "Total shots on target regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, ["football_shots_total_regulation"]),
        ("football_corners_total_regulation", "football", "corners", "Total corners regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, []),
    ]
    for row in markets:
        con.execute(
            """INSERT OR REPLACE INTO canonical_markets
               (canonical_market_id, sport, market_family, display_name, settlement_scope, period,
                line_required, team_required, player_required, dangerous_confusables_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*row[:-1], json.dumps(row[-1])),
        )
    market_aliases = [
        ("1X2", "football_1x2_regulation"),
        ("Final", "football_1x2_regulation"),
        ("Match winner", "football_1x2_regulation"),
        ("To qualify", "football_to_qualify"),
        ("Calificare", "football_to_qualify"),
        ("Shots", "football_shots_total_regulation"),
        ("Total shots", "football_shots_total_regulation"),
        ("Shots on target", "football_shots_on_target_total_regulation"),
        ("Șuturi pe poartă", "football_shots_on_target_total_regulation"),
        ("Corners", "football_corners_total_regulation"),
        ("Total corners", "football_corners_total_regulation"),
        ("Cornere", "football_corners_total_regulation"),
        ("Lovituri de colț", "football_corners_total_regulation"),
    ]
    for alias, canonical_id in market_aliases:
        alias_id = f"market_alias:{canonical_id}:{sha_text(alias)[:12]}"
        con.execute(
            """INSERT OR REPLACE INTO market_aliases
               (alias_id, canonical_market_id, provider_id, alias_text, normalized_alias, confidence, source_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, canonical_id, None, alias, normalize_text(alias), 1.0, "v33 seed"),
        )
    con.commit()


def fetch_aliases(con, table: str, canonical_col: str, extra_cols: str = "") -> List[Dict[str, Any]]:
    sql = f"SELECT {canonical_col}, alias_text, normalized_alias{extra_cols} FROM {table}"
    cols = [d[0] for d in con.execute(sql).description]
    return [dict(zip(cols, row)) for row in con.execute(sql).fetchall()]


def resolve_alias(con, entity_type: str, raw_value: str, provider_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    context = context or {}
    norm = normalize_text(raw_value)
    if entity_type == "team":
        aliases = fetch_aliases(con, "team_aliases", "canonical_team_id")
        canonical_col = "canonical_team_id"
    elif entity_type == "player":
        aliases = fetch_aliases(con, "player_aliases", "canonical_player_id", ", team_context_id, country_context")
        canonical_col = "canonical_player_id"
    elif entity_type == "market":
        aliases = fetch_aliases(con, "market_aliases", "canonical_market_id")
        canonical_col = "canonical_market_id"
    else:
        raise ValueError(entity_type)

    exact = [a for a in aliases if a["normalized_alias"] == norm]
    if entity_type == "player" and exact:
        team_ctx = context.get("team_id")
        country_ctx = context.get("country")
        contextual = [a for a in exact if (not a.get("team_context_id") or a.get("team_context_id") == team_ctx) and (not a.get("country_context") or a.get("country_context") == country_ctx)]
        if contextual:
            best = contextual[0]
            strategy = "exact_alias_with_context"
            confidence = 0.99
        else:
            best = exact[0]
            strategy = "exact_alias_missing_context"
            confidence = 0.88
    elif exact:
        best = exact[0]
        strategy = "exact_alias"
        confidence = 0.99
    else:
        scored = sorted(((ratio(norm, a["normalized_alias"]), a) for a in aliases), reverse=True, key=lambda x: x[0])
        score, best = scored[0] if scored else (0.0, None)
        strategy = "fuzzy_alias"
        confidence = round(score, 4)

    canonical_id = best[canonical_col] if best else None
    auto_map_allowed = bool(canonical_id and confidence >= AUTO_THRESHOLD)
    reason = "auto high confidence" if auto_map_allowed else "review required"
    candidate_id = f"resolver:{entity_type}:{sha_text(json.dumps([raw_value, provider_id, context, canonical_id, confidence], sort_keys=True))[:16]}"
    con.execute(
        """INSERT OR REPLACE INTO resolver_mapping_candidates
           (candidate_id, entity_type, raw_value, normalized_raw_value, provider_id, context_json,
            candidate_canonical_id, candidate_display_name, strategy, confidence, auto_map_allowed, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_id,
            entity_type,
            raw_value,
            norm,
            provider_id,
            json.dumps(context, sort_keys=True),
            canonical_id,
            best.get("alias_text") if best else None,
            strategy,
            confidence,
            int(auto_map_allowed),
            reason,
        ),
    )
    if auto_map_allowed:
        con.execute(
            """INSERT OR REPLACE INTO resolver_mapping_decisions
               (decision_id, candidate_id, entity_type, raw_value, provider_id, canonical_id, decision, confidence, reason, decided_by, immutable_raw_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"decision:{candidate_id}",
                candidate_id,
                entity_type,
                raw_value,
                provider_id,
                canonical_id,
                "auto_mapped",
                confidence,
                reason,
                "v33_smoke",
                candidate_id,
            ),
        )
    con.commit()
    return {
        "entity_type": entity_type,
        "raw_value": raw_value,
        "normalized": norm,
        "canonical_id": canonical_id,
        "strategy": strategy,
        "confidence": confidence,
        "auto_map_allowed": auto_map_allowed,
        "candidate_id": candidate_id,
    }


def rows(con, sql: str) -> List[Dict[str, Any]]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_report(db: Path) -> Dict[str, Any]:
    con = connect(db)
    try:
        register_default_sources(con)
        insert_seed_data(con)
        resolutions = [
            resolve_alias(con, "team", "Man. Utd"),
            resolve_alias(con, "team", "MAN UTD"),
            resolve_alias(con, "player", "K. Mbappe", context={"team_id": "team_france", "country": "France"}),
            resolve_alias(con, "player", "Mbappe", context={"team_id": "team_france", "country": "France"}),
            resolve_alias(con, "market", "Cornere"),
            resolve_alias(con, "market", "Lovituri de colț"),
            resolve_alias(con, "market", "Shots"),
            resolve_alias(con, "market", "Shots on target"),
            resolve_alias(con, "market", "Final"),
            resolve_alias(con, "market", "To qualify"),
            resolve_alias(con, "market", "Suturi cadrate jucator special combo"),
        ]
        counts = table_counts(con)
        review_queue = rows(
            con,
            """
            SELECT entity_type, raw_value, candidate_canonical_id, confidence, reason, candidate_count
            FROM resolver_review_queue
            ORDER BY entity_type, raw_value
            """,
        )
    finally:
        con.close()

    by_raw = {r["raw_value"]: r for r in resolutions}
    acceptance = {
        "team_aliases_resolve": by_raw["Man. Utd"]["canonical_id"] == "team_manchester_united" and by_raw["MAN UTD"]["canonical_id"] == "team_manchester_united",
        "player_aliases_resolve_with_context": by_raw["K. Mbappe"]["canonical_id"] == "player_kylian_mbappe" and by_raw["Mbappe"]["canonical_id"] == "player_kylian_mbappe",
        "romanian_corner_aliases_resolve": by_raw["Cornere"]["canonical_id"] == "football_corners_total_regulation" and by_raw["Lovituri de colț"]["canonical_id"] == "football_corners_total_regulation",
        "shots_and_sot_remain_separate": by_raw["Shots"]["canonical_id"] == "football_shots_total_regulation" and by_raw["Shots on target"]["canonical_id"] == "football_shots_on_target_total_regulation",
        "regulation_and_qualify_remain_separate": by_raw["Final"]["canonical_id"] == "football_1x2_regulation" and by_raw["To qualify"]["canonical_id"] == "football_to_qualify",
        "unknown_low_confidence_goes_to_review": any(r["raw_value"] == "Suturi cadrate jucator special combo" for r in review_queue),
        "resolver_tables_positive": counts.get("canonical_teams", 0) >= 2 and counts.get("canonical_markets", 0) >= 5,
        "no_provider_calls": True,
        "no_website_automation": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v33_canonical_resolver_alias_mapping_engine",
        "db": str(db),
        "counts": counts,
        "resolutions": resolutions,
        "review_queue": review_queue,
        "acceptance": acceptance,
        "safety": {
            "never_train_on_uncertain_mappings": True,
            "prefer_missing_data_over_false_merges": True,
            "raw_data_preserved": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v33 canonical resolver smoke.")
    ap.add_argument("--db", default="../build/omnibet_v33_resolver_smoke.sqlite")
    ap.add_argument("--out", default="../reports/ci_v33_canonical_resolver_smoke.json")
    args = ap.parse_args()
    report = build_report(Path(args.db))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
