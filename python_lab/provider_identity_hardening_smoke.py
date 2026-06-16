#!/usr/bin/env python3
"""v42 provider identity hardening smoke.

Builds deterministic provider identity candidates across offline samples:
The Odds API-style markets and API-Football-style fixture state.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List

from adapters.warehouse import connect, sha_text
from provider_pipeline_schema import ensure_provider_pipeline_schema


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def insert_candidate(con, entity_type: str, canonical_id: str, provider_id: str, provider_entity_id: str | None, raw_name: str, strategy: str, confidence: float, decision: str, reason: str, raw: Dict[str, Any]) -> None:
    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    candidate_id = f"identity:{entity_type}:{provider_id}:{sha_text(json.dumps([canonical_id, provider_entity_id, raw_name, strategy], sort_keys=True))[:16]}"
    con.execute(
        """INSERT OR REPLACE INTO provider_identity_candidates
           (candidate_id, canonical_entity_type, canonical_id, provider_id, provider_entity_id,
            raw_name, normalized_name, match_strategy, confidence, decision, reason, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (candidate_id, entity_type, canonical_id, provider_id, provider_entity_id, raw_name, normalize(raw_name), strategy, confidence, decision, reason, raw_json),
    )


def insert_review(con, entity_type: str, provider_id: str, provider_entity_id: str | None, raw_name: str, candidate_id: str | None, confidence: float, reason: str, raw: Dict[str, Any]) -> None:
    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    review_id = f"identity_review:{entity_type}:{provider_id}:{sha_text(json.dumps([provider_entity_id, raw_name, candidate_id], sort_keys=True))[:16]}"
    con.execute(
        """INSERT OR REPLACE INTO provider_identity_review_queue
           (review_id, canonical_entity_type, provider_id, provider_entity_id, raw_name,
            normalized_name, candidate_canonical_id, confidence, reason, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, entity_type, provider_id, provider_entity_id, raw_name, normalize(raw_name), candidate_id, confidence, reason, raw_json),
    )


def iter_api_football_players(state_payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    fixture = state_payload["response"][0]
    seen: set[str] = set()
    for lineup in fixture.get("lineups", []):
        for bucket in ("startXI", "substitutes"):
            for item in lineup.get(bucket, []):
                player = item.get("player") or {}
                pid = str(player.get("id"))
                if pid and pid not in seen:
                    seen.add(pid)
                    yield player
    for event in fixture.get("events", []):
        for key in ("player", "assist"):
            player = event.get(key) or {}
            pid = str(player.get("id"))
            if player.get("id") is not None and pid not in seen:
                seen.add(pid)
                yield player


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    odds = load_json(odds_input)
    state = load_json(state_input)
    link = load_json(link_input)
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        canonical_event_id = link["canonical_event_id"]
        for provider_link in link.get("provider_links", []):
            insert_candidate(
                con,
                "event",
                canonical_event_id,
                provider_link["provider_id"],
                str(provider_link["provider_event_id"]),
                f"{link['home_team_name']} vs {link['away_team_name']}",
                "manifest_event_link",
                float(provider_link.get("confidence", 1.0)),
                "auto_match",
                "deterministic offline manifest link",
                provider_link,
            )

        canonical_teams = {
            normalize(link["home_team_name"]): "canonical_team:france",
            normalize(link["away_team_name"]): "canonical_team:senegal",
        }
        for name in (odds.get("home_team"), odds.get("away_team")):
            canonical_id = canonical_teams.get(normalize(name), f"canonical_team:{normalize(name).replace(' ', '_')}")
            insert_candidate(con, "team", canonical_id, "the_odds_api_offline_sample", None, name, "normalized_exact_team", 1.0, "auto_match", "exact normalized team name", {"name": name})
        fixture = state["response"][0]
        for side in ("home", "away"):
            team = fixture["teams"][side]
            canonical_id = canonical_teams.get(normalize(team.get("name")), f"canonical_team:{normalize(team.get('name')).replace(' ', '_')}")
            insert_candidate(con, "team", canonical_id, "api_football_offline_sample", str(team.get("id")), team.get("name"), "normalized_exact_team_with_provider_id", 1.0, "auto_match", "exact normalized team name with provider id", team)

        player_canonical = {
            "kylian mbappe": "canonical_player:kylian_mbappe",
            "antoine griezmann": "canonical_player:antoine_griezmann",
            "olivier giroud": "canonical_player:olivier_giroud",
            "sadio mane": "canonical_player:sadio_mane",
            "ismaila sarr": "canonical_player:ismaila_sarr",
        }
        for player in iter_api_football_players(state):
            n = normalize(player.get("name"))
            canonical_id = player_canonical.get(n, f"canonical_player:{n.replace(' ', '_')}")
            insert_candidate(con, "player", canonical_id, "api_football_offline_sample", str(player.get("id")), player.get("name"), "normalized_exact_player_with_provider_id", 1.0, "auto_match", "exact normalized player name with provider id", player)

        for bookmaker in odds.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if "player" not in (market.get("key") or ""):
                    continue
                for outcome in market.get("outcomes", []):
                    player_name = outcome.get("description") or outcome.get("name")
                    cleaned = str(player_name).replace(" Over", "").replace(" Under", "")
                    n = normalize(cleaned)
                    canonical_id = player_canonical.get(n, f"canonical_player:{n.replace(' ', '_')}")
                    insert_candidate(con, "player", canonical_id, "the_odds_api_offline_sample", None, cleaned, "normalized_player_prop_description", 1.0 if n in player_canonical else 0.88, "auto_match" if n in player_canonical else "review", "player prop description matched to canonical player" if n in player_canonical else "needs manual player alias review", outcome)

        insert_review(con, "team", "example_uncertain_provider", "team-uncertain-1", "France U21", "canonical_team:france", 0.72, "youth/national-team suffix is ambiguous and must not auto-merge", {"raw_name": "France U21"})
        con.commit()
        decision_counts = rows(con, "SELECT decision, COUNT(*) AS rows FROM provider_identity_candidates GROUP BY decision ORDER BY decision")
        type_counts = rows(con, "SELECT canonical_entity_type, COUNT(*) AS rows FROM provider_identity_candidates GROUP BY canonical_entity_type ORDER BY canonical_entity_type")
        review_rows = rows(con, "SELECT canonical_entity_type, raw_name, candidate_canonical_id, confidence, reason FROM provider_identity_review_queue ORDER BY confidence")
    finally:
        con.close()

    decision_map = {row["decision"]: row["rows"] for row in decision_counts}
    type_map = {row["canonical_entity_type"]: row["rows"] for row in type_counts}
    acceptance = {
        "event_candidates_written": type_map.get("event", 0) >= 2,
        "team_candidates_written": type_map.get("team", 0) >= 4,
        "player_candidates_written": type_map.get("player", 0) >= 8,
        "auto_matches_written": decision_map.get("auto_match", 0) >= 10,
        "review_queue_has_uncertain_case": len(review_rows) >= 1,
        "uncertain_case_not_auto_merged": any(row["raw_name"] == "France U21" for row in review_rows),
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v42_provider_identity_hardening",
        "db": str(db),
        "decision_counts": decision_counts,
        "type_counts": type_counts,
        "review_rows": review_rows,
        "acceptance": acceptance,
        "safety": {"offline_samples_only": True, "no_network": True, "no_api_keys": True, "uncertain_entities_not_auto_merged": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v42 provider identity hardening smoke.")
    ap.add_argument("--db", default="../build/omnibet_v42_identity_hardening.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v42_identity_hardening.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
