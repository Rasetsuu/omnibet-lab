#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'configs/football_data_batch_001.v941_v960.json'


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def build_report(require_data: bool = False) -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH)
    paths = cfg['paths']
    source = cfg['source']
    gates = cfg['gates']

    raw_csv = ROOT / paths['raw_csv']
    matches_jsonl = ROOT / paths['matches_jsonl']
    odds_jsonl = ROOT / paths['odds_jsonl']
    import_report_path = ROOT / paths['import_report']
    feature_counts_path = ROOT / paths['feature_counts_report']
    runner = ROOT / 'scripts/run_football_data_batch_001.sh'
    docs = ROOT / 'docs/v941_football_data_batch_001.md'

    data_checks = {
        'raw_csv_present': raw_csv.exists(),
        'matches_jsonl_present': matches_jsonl.exists(),
        'odds_jsonl_present': odds_jsonl.exists(),
        'import_report_present': import_report_path.exists(),
        'feature_counts_present': feature_counts_path.exists(),
    }

    manifest_checks = {
        'schema': cfg.get('schema') == 'omnibet.football_data_batch_001.v941_v960',
        'paper_only': cfg.get('paper_only') is True,
        'local_first': cfg.get('local_first') is True,
        'ci_downloads_disabled': cfg.get('ci_downloads_allowed') is False,
        'live_provider_calls_disabled': cfg.get('live_provider_calls_allowed') is False,
        'raw_csv_not_committed_default': cfg.get('commit_raw_csv') is False,
        'source_provider': source.get('provider') == 'Football-Data.co.uk',
        'source_url_declared': source.get('source_url', '').startswith('https://www.football-data.co.uk/'),
        'competition_declared': source.get('competition_id') == 'england_premier_league',
        'season_declared': source.get('season_id') == '2024_2025',
        'row_gate_declared': gates.get('minimum_rows_for_v1_baseline') == 200,
        'real_model_stays_locked': gates.get('real_model_ready_after_count_gate') is False,
        'runner_added': runner.exists(),
        'docs_added': docs.exists(),
        'raw_path_under_local_historical': paths['raw_csv'].startswith('data/local_historical/football_data/raw/'),
        'feature_counts_report_path': paths['feature_counts_report'] == 'reports/feature_counts.json',
    }

    generated_counts: Dict[str, Any] = {}
    generated_ok = False
    if feature_counts_path.exists():
        generated_counts = read_json(feature_counts_path)
        generated_ok = (
            generated_counts.get('schema') == 'omnibet.feature_count_gate.v921'
            and int(generated_counts.get('eligible_feature_rows', 0)) >= int(gates['minimum_rows_for_v1_baseline'])
            and generated_counts.get('baseline_training_allowed') is True
            and generated_counts.get('real_model_ready') is False
        )

    if require_data:
        ok = all(manifest_checks.values()) and all(data_checks.values()) and generated_ok
        status = 'batch_001_ready' if ok else 'batch_001_blocked_or_incomplete'
    else:
        ok = all(manifest_checks.values())
        status = 'manifest_ready_waiting_for_local_raw_csv'

    return {
        'ok': ok,
        'schema': 'omnibet.football_data_batch_001_check.v941_v960',
        'status': status,
        'require_data': require_data,
        'manifest_checks': manifest_checks,
        'data_checks': data_checks,
        'generated_counts': generated_counts,
        'next_action': 'download the declared Football-Data CSV locally and run scripts/run_football_data_batch_001.sh' if not data_checks['raw_csv_present'] else 'run scripts/run_football_data_batch_001.sh',
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-data', action='store_true', help='Require raw/normalized data and a passing feature_counts.json report.')
    parser.add_argument('--out', default='reports/ci_v941_v960_football_data_batch_001.json')
    args = parser.parse_args()
    report = build_report(require_data=args.require_data)
    write_json(ROOT / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
