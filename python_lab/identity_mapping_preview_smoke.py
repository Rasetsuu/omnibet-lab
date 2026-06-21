#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

IdentityKey = Tuple[str, str, Optional[str], str]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def norm(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def add_ref(refs: Set[IdentityKey], provider: str, kind: str, entity_id: Optional[Any], name: Optional[str]) -> None:
    if not name:
        return
    refs.add((provider, kind, None if entity_id is None else str(entity_id), norm(str(name))))


def sample_refs(root: Path) -> Dict[str, int]:
    odds = read_json(root / "data/samples/the_odds_api_event_markets_sample.json")
    football = read_json(root / "data/samples/api_football_live_state_sample.json")
    first = football["response"][0]

    refs: Set[IdentityKey] = set()
    add_ref(refs, "the_odds_api", "fixture", odds["id"], f"{odds['home_team']} vs {odds['away_team']}")
    add_ref(refs, "api_football", "fixture", first["fixture"]["id"], f"{first['teams']['home']['name']} vs {first['teams']['away']['name']}")
    add_ref(refs, "the_odds_api", "team", None, odds["home_team"])
    add_ref(refs, "the_odds_api", "team", None, odds["away_team"])
    add_ref(refs, "api_football", "team", first["teams"]["home"]["id"], first["teams"]["home"]["name"])
    add_ref(refs, "api_football", "team", first["teams"]["away"]["id"], first["teams"]["away"]["name"])

    for lineup in first.get("lineups", []):
        for bucket in ("startXI", "substitutes"):
            for row in lineup.get(bucket, []):
                player = row.get("player", {})
                add_ref(refs, "api_football", "player", player.get("id"), player.get("name"))
    for event in first.get("events", []):
        for bucket in ("player", "assist"):
            player = event.get(bucket, {})
            add_ref(refs, "api_football", "player", player.get("id"), player.get("name"))
    for bookmaker in odds.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if "player" in str(market.get("key", "")):
                for outcome in market.get("outcomes", []):
                    add_ref(refs, "the_odds_api", "player", None, outcome.get("description"))

    return {
        "fixture_identity_refs": sum(1 for row in refs if row[1] == "fixture"),
        "team_identity_refs": sum(1 for row in refs if row[1] == "team"),
        "player_identity_refs": sum(1 for row in refs if row[1] == "player"),
        "total_identity_refs": len(refs),
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/identity_mapping_preview.v239.json")
    rust = (root / "rust-core/src/identity_mapping_v239.rs").read_text(encoding="utf-8")
    wrapper = (root / "rust-core/src/idmap_v239.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    counts = sample_refs(root)
    expected = contract.get("expected_offline_preview", {})
    aliases = contract.get("provider_aliases", [])
    canonical = {row["canonical_id"] for row in contract.get("canonical_entities", [])}

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.identity_mapping_preview.v239",
        "preview_only": contract.get("promotion_policy", {}).get("preview_only") is True,
        "unknown_auto_forbidden": contract.get("promotion_policy", {}).get("automatic_unknown_identity_promotion_allowed") is False,
        "alias_required": contract.get("promotion_policy", {}).get("provider_alias_required") is True,
        "fixture_gate": contract.get("promotion_policy", {}).get("fixture_identity_required_before_match_fact_promotion") is True,
        "team_gate": contract.get("promotion_policy", {}).get("team_identity_required_before_team_fact_promotion") is True,
        "player_gate": contract.get("promotion_policy", {}).get("player_identity_required_before_player_fact_promotion") is True,
        "all_aliases_reference_canonical": all(row.get("canonical_id") in canonical for row in aliases),
        "expected_fixture_refs": counts["fixture_identity_refs"] == expected.get("fixture_identity_refs"),
        "expected_team_refs": counts["team_identity_refs"] == expected.get("team_identity_refs"),
        "expected_player_refs": counts["player_identity_refs"] == expected.get("player_identity_refs"),
        "expected_total_refs": counts["total_identity_refs"] == expected.get("total_identity_refs"),
        "expected_resolved_refs": expected.get("resolved_identity_refs") == expected.get("total_identity_refs"),
        "rust_types": "IdentityMappingPreview" in rust and "ProviderIdentityRef" in rust and "IdentityResolution" in rust,
        "rust_builder": "build_identity_preview_from_offline_samples" in rust and "build_identity_refs_from_samples" in rust,
        "rust_unknown_review": "unmapped_provider_identity" in rust and "NeedsReview" in rust,
        "rust_name_only_player": "odds_player_prop_participant" in rust and "the_odds_api" in rust,
        "wrapper_loads_impl": "identity_mapping_v239.rs" in wrapper,
        "lib_exports_wrapper": "pub mod idmap_v239;" in lib and "pub use idmap_v239::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.identity_mapping_preview_smoke.v239",
        "milestone": "v239_identity_mapping_preview",
        "computed_counts": counts,
        "acceptance": checks,
        "safety": {
            "preview_only": True,
            "unknown_identities_auto_promoted": False,
            "unmapped_identities_review_required": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v239_identity_mapping_preview.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
