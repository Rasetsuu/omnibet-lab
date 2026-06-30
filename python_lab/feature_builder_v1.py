#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def slug(value: str) -> str:
    return value.lower().replace(' ', '-').replace('/', '-')


def result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return 'home_win'
    if home_score < away_score:
        return 'away_win'
    return 'draw'


def load_csv_matches(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            home_score = int(row['FTHG'])
            away_score = int(row['FTAG'])
            rows.append({
                'fixture_id': f"csv-{slug(row['HomeTeam'])}-{slug(row['AwayTeam'])}-{row['Date']}",
                'kickoff_utc': f"{row['Date']}T00:00:00Z",
                'home_name': row['HomeTeam'],
                'away_name': row['AwayTeam'],
                'home_score': home_score,
                'away_score': away_score,
                'result_label': result_label(home_score, away_score),
                'total_goals': home_score + away_score,
                'label_available_after_utc': f"{row['Date']}T23:59:00Z",
            })
    return sorted(rows, key=lambda item: (item['kickoff_utc'], item['fixture_id']))


def empty_team_state() -> Dict[str, float]:
    return {
        'matches': 0,
        'points': 0,
        'goals_for': 0,
        'goals_against': 0,
    }


def avg(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def points_for(score_for: int, score_against: int) -> int:
    if score_for > score_against:
        return 3
    if score_for == score_against:
        return 1
    return 0


def build_features(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    team_state: Dict[str, Dict[str, float]] = {}
    features: List[Dict[str, Any]] = []
    for match in matches:
        home = match['home_name']
        away = match['away_name']
        home_state = dict(team_state.get(home, empty_team_state()))
        away_state = dict(team_state.get(away, empty_team_state()))
        home_matches = home_state['matches']
        away_matches = away_state['matches']
        feature_row = {
            'fixture_id': match['fixture_id'],
            'kickoff_utc': match['kickoff_utc'],
            'home_name': home,
            'away_name': away,
            'home_field': 1,
            'home_history_matches_before_kickoff': int(home_matches),
            'away_history_matches_before_kickoff': int(away_matches),
            'home_points_per_match_before_kickoff': avg(home_state['points'], home_matches),
            'away_points_per_match_before_kickoff': avg(away_state['points'], away_matches),
            'home_goals_for_avg_before_kickoff': avg(home_state['goals_for'], home_matches),
            'away_goals_for_avg_before_kickoff': avg(away_state['goals_for'], away_matches),
            'home_goals_against_avg_before_kickoff': avg(home_state['goals_against'], home_matches),
            'away_goals_against_avg_before_kickoff': avg(away_state['goals_against'], away_matches),
            'label_result': match['result_label'],
            'label_total_goals': match['total_goals'],
            'label_available_after_utc': match['label_available_after_utc'],
            'timestamp_safe': match['label_available_after_utc'] > match['kickoff_utc'],
            'history_ready': home_matches >= 3 and away_matches >= 3,
        }
        features.append(feature_row)

        home_update = team_state.setdefault(home, empty_team_state())
        away_update = team_state.setdefault(away, empty_team_state())
        home_update['matches'] += 1
        away_update['matches'] += 1
        home_update['points'] += points_for(match['home_score'], match['away_score'])
        away_update['points'] += points_for(match['away_score'], match['home_score'])
        home_update['goals_for'] += match['home_score']
        home_update['goals_against'] += match['away_score']
        away_update['goals_for'] += match['away_score']
        away_update['goals_against'] += match['home_score']
    return features


def build_report(root: Path) -> Dict[str, Any]:
    cfg = read_json(root / 'configs/feature_builder_v1.v801_v830.json')
    matches = load_csv_matches(root / cfg['inputs']['csv_match_sample'])
    feature_rows = build_features(matches)
    thresholds = cfg['thresholds']
    payload = {
        'schema': 'omnibet.feature_rows.v801_v830',
        'ready_for_v1_baseline': len(feature_rows) >= thresholds['minimum_rows_for_v1_baseline'],
        'row_count': len(feature_rows),
        'minimum_rows_for_v1_baseline': thresholds['minimum_rows_for_v1_baseline'],
        'rows': feature_rows,
    }
    write_json(root / cfg['outputs']['feature_rows'], payload)
    checks = {
        'schema': cfg.get('schema') == 'omnibet.feature_builder_v1.v801_v830',
        'feature_row_count': len(feature_rows) >= thresholds['minimum_rows_for_feature_smoke'],
        'timestamp_safe': all(row['timestamp_safe'] for row in feature_rows),
        'not_ready_for_v1_baseline': payload['ready_for_v1_baseline'] is False,
        'required_features_present': all(name in feature_rows[0] for name in cfg['features']),
        'feature_rows_written': (root / cfg['outputs']['feature_rows']).exists(),
    }
    return {
        'ok': all(checks.values()),
        'schema': 'omnibet.feature_builder_v1_smoke.v801_v830',
        'checks': checks,
        'summary': {
            'feature_rows': len(feature_rows),
            'ready_for_v1_baseline': payload['ready_for_v1_baseline'],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--out', default='reports/ci_v801_v830_feature_builder_v1.json')
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    write_json(root / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
