#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def league(competition_id: str, name: str, country: str, group: str, scope: str, priority: int, *, tier: int = 1, kind: str = "domestic_league") -> Dict[str, Any]:
    return {
        "competition_id": competition_id,
        "name": name,
        "country_or_region": country,
        "region_group": group,
        "tier": tier,
        "competition_kind": kind,
        "default_scope": scope,
        "priority": priority,
        "train_separately": scope in {"core_train", "expanded_train"},
        "calibrate_separately": scope in {"core_train", "expanded_train"},
        "reference_only": scope == "reference_only",
    }


LEAGUES: List[Dict[str, Any]] = [
    # Europe core tier 1
    league("eng_premier", "Premier League", "England", "europe_uk", "core_train", 100),
    league("esp_laliga", "La Liga", "Spain", "europe", "core_train", 99),
    league("ita_serie_a", "Serie A", "Italy", "europe", "core_train", 98),
    league("ger_bundesliga", "Bundesliga", "Germany", "europe", "core_train", 97),
    league("fra_ligue1", "Ligue 1", "France", "europe", "core_train", 96),
    league("por_primeira", "Primeira Liga", "Portugal", "europe", "core_train", 92),
    league("ned_eredivisie", "Eredivisie", "Netherlands", "europe", "core_train", 91),
    league("bel_pro_league", "Belgian Pro League", "Belgium", "europe", "core_train", 88),
    league("sco_premiership", "Scottish Premiership", "Scotland", "europe_uk", "core_train", 86),
    league("aut_bundesliga", "Austrian Bundesliga", "Austria", "europe", "expanded_train", 80),
    league("sui_super_league", "Swiss Super League", "Switzerland", "europe", "expanded_train", 80),
    league("den_superliga", "Danish Superliga", "Denmark", "europe", "expanded_train", 78),
    league("nor_eliteserien", "Eliteserien", "Norway", "europe", "expanded_train", 77),
    league("swe_allsvenskan", "Allsvenskan", "Sweden", "europe", "expanded_train", 77),
    league("pol_ekstraklasa", "Ekstraklasa", "Poland", "europe", "expanded_train", 75),
    league("cze_first_league", "Czech First League", "Czech Republic", "europe", "expanded_train", 74),
    league("gre_super_league", "Greek Super League", "Greece", "europe", "expanded_train", 73),
    league("tur_super_lig", "Super Lig", "Turkey", "europe", "expanded_train", 78),
    league("rou_liga1", "Romania Liga I", "Romania", "europe", "expanded_train", 70),
    league("ukr_premier", "Ukrainian Premier League", "Ukraine", "europe", "expanded_train", 69),
    league("cro_hnl", "Croatia HNL", "Croatia", "europe", "expanded_train", 68),
    league("srb_superliga", "Serbian SuperLiga", "Serbia", "europe", "expanded_train", 67),
    league("bul_first", "Bulgaria First League", "Bulgaria", "europe", "expanded_train", 66),
    # UK depth
    league("eng_championship", "EFL Championship", "England", "europe_uk", "expanded_train", 84, tier=2),
    league("eng_league_one", "EFL League One", "England", "europe_uk", "expanded_train", 72, tier=3),
    league("eng_league_two", "EFL League Two", "England", "europe_uk", "expanded_train", 66, tier=4),
    league("irl_premier", "League of Ireland Premier", "Ireland", "europe_uk", "expanded_train", 64),
    league("nir_premiership", "Northern Ireland Premiership", "Northern Ireland", "europe_uk", "reference_only", 50),
    league("wal_cymru_premier", "Cymru Premier", "Wales", "europe_uk", "reference_only", 50),
    # Americas
    league("usa_mls", "MLS", "USA", "americas", "core_train", 84),
    league("usa_usl_championship", "USL Championship", "USA", "americas", "expanded_train", 68, tier=2),
    league("mex_liga_mx", "Liga MX", "Mexico", "americas", "core_train", 84),
    league("can_premier", "Canadian Premier League", "Canada", "americas", "expanded_train", 63),
    league("arg_primera", "Argentina Primera Division", "Argentina", "americas", "core_train", 86),
    league("bra_serie_a", "Brazil Serie A", "Brazil", "americas", "core_train", 87),
    league("col_primera_a", "Colombia Primera A", "Colombia", "americas", "expanded_train", 72),
    league("chi_primera", "Chile Primera Division", "Chile", "americas", "expanded_train", 70),
    league("uru_primera", "Uruguay Primera Division", "Uruguay", "americas", "expanded_train", 68),
    league("par_primera", "Paraguay Primera Division", "Paraguay", "americas", "expanded_train", 66),
    league("ecu_serie_a", "Ecuador Serie A", "Ecuador", "americas", "expanded_train", 66),
    league("per_liga1", "Peru Liga 1", "Peru", "americas", "expanded_train", 64),
    # Selected non-Europe domestic leagues
    league("jpn_j1", "J1 League", "Japan", "asia_oceania", "expanded_train", 76),
    league("kor_k1", "K League 1", "South Korea", "asia_oceania", "expanded_train", 74),
    league("chn_super", "Chinese Super League", "China", "asia_oceania", "reference_only", 58),
    league("aus_a_league", "A-League", "Australia", "asia_oceania", "expanded_train", 67),
    league("ksa_pro", "Saudi Pro League", "Saudi Arabia", "asia_oceania", "expanded_train", 72),
    league("egy_premier", "Egyptian Premier League", "Egypt", "africa", "expanded_train", 66),
    league("rsa_psl", "South Africa Premier Soccer League", "South Africa", "africa", "expanded_train", 64),
    # Continental and special competitions
    league("uefa_champions", "UEFA Champions League", "Europe", "special", "core_train", 95, kind="continental_club"),
    league("uefa_europa", "UEFA Europa League", "Europe", "special", "core_train", 88, kind="continental_club"),
    league("uefa_conference", "UEFA Europa Conference League", "Europe", "special", "expanded_train", 76, kind="continental_club"),
    league("uefa_super_cup", "UEFA Super Cup", "Europe", "special", "reference_only", 45, kind="super_cup"),
    league("fifa_world_cup", "FIFA World Cup", "World", "special", "core_train", 96, kind="national_team"),
    league("uefa_euro", "UEFA Euro", "Europe", "special", "core_train", 90, kind="national_team"),
    league("uefa_nations", "UEFA Nations League", "Europe", "special", "expanded_train", 72, kind="national_team"),
    league("copa_america", "Copa America", "South America", "special", "expanded_train", 78, kind="national_team"),
    league("afcon", "Africa Cup of Nations", "Africa", "special", "expanded_train", 70, kind="national_team"),
    league("copa_libertadores", "Copa Libertadores", "South America", "special", "core_train", 86, kind="continental_club"),
    league("copa_sudamericana", "Copa Sudamericana", "South America", "special", "expanded_train", 76, kind="continental_club"),
    league("concacaf_champions", "CONCACAF Champions Cup", "North America", "special", "expanded_train", 70, kind="continental_club"),
    league("afc_champions", "AFC Champions League", "Asia", "special", "expanded_train", 72, kind="continental_club"),
    league("leagues_cup", "Leagues Cup", "North America", "special", "reference_only", 54, kind="cross_border_cup"),
]


def build_universe() -> Dict[str, Any]:
    groups: Dict[str, int] = {}
    for row in LEAGUES:
        groups[row["region_group"]] = groups.get(row["region_group"], 0) + 1
    core = [r for r in LEAGUES if r["default_scope"] == "core_train"]
    trainable = [r for r in LEAGUES if r["default_scope"] in {"core_train", "expanded_train"}]
    return {
        "ok": True,
        "schema": "omnibet.league_universe.v86b",
        "selection_policy": {
            "include": ["high-signal tier-1 domestic leagues", "major UK depth", "major Americas leagues", "continental/special competitions", "selected high-signal non-Europe leagues"],
            "exclude_by_default": ["youth", "reserve", "low-signal lower divisions", "duplicate regional cups", "women competitions until separate model path exists"],
            "footystats_role": "reference_index_only_not_scrape_target",
        },
        "row_counts": {"total": len(LEAGUES), "core_train": len(core), "trainable": len(trainable), "reference_only": len(LEAGUES) - len(trainable), "groups": groups},
        "leagues": sorted(LEAGUES, key=lambda r: (-r["priority"], r["competition_id"])),
        "safety": {"offline_only": True, "no_website_automation": True, "manual_or_permitted_sources_only": True},
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(out: Path, sample: Path | None) -> Dict[str, Any]:
    universe = build_universe()
    if sample:
        write_json(sample, universe)
    counts = universe["row_counts"]
    groups = counts["groups"]
    checks = {
        "total_at_least_45": counts["total"] >= 45,
        "trainable_at_least_30": counts["trainable"] >= 30,
        "core_at_least_10": counts["core_train"] >= 10,
        "has_europe": groups.get("europe", 0) >= 15,
        "has_uk": groups.get("europe_uk", 0) >= 5,
        "has_americas": groups.get("americas", 0) >= 8,
        "has_special": groups.get("special", 0) >= 8,
        "has_non_europe": groups.get("asia_oceania", 0) + groups.get("africa", 0) >= 5,
        "sample_written": sample is not None and sample.exists(),
        "no_website_automation": universe["safety"]["no_website_automation"] is True,
    }
    report = {"ok": all(checks.values()), "milestone": "v86b_league_universe", "acceptance": checks, "universe": universe}
    write_json(out, report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/ci_v86b_league_universe.json")
    ap.add_argument("--sample", default="tauri-app/src/league-universe.sample.json")
    args = ap.parse_args()
    report = build_report(Path(args.out), Path(args.sample) if args.sample else None)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
