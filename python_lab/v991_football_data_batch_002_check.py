#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'configs/football_data_batch_002.v991_v1030.json'


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding='utf-8').splitlines() if line.strip())


def build_report(require_data: bool = False) -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH)
    sources = cfg.get('sources', [])
    aggregate_paths = cfg['aggregate_paths']
    targets = cfg['batch_targets']

    raw_presence = {source['raw_csv']: (ROOT / source['raw_csv']).exists() for source in sources}
    normalized_presence = {
        source['normalized_dir']: (ROOT / source['normalized_dir'] / 'matches.jsonl').exists()
        for source in sources
    }
    aggregate_matches = ROOT / aggregate_paths['matches_jsonl']
    aggregate_odds = ROOT / aggregate_paths['odds_jsonl']
    feature_counts_path = ROOT / aggregate_paths['feature_counts_report']
    model_eval_path = ROOT / aggregate_paths['model_eval_report']

    manifest_checks = {
        'schema': cfg.get('schema') == 'omnibet.football_data_batch_002.v991_v1030',
        'paper_only': cfg.get('paper_only') is True,
        'local_first': cfg.get('local_first') is True,
        'ci_downloads_disabled': cfg.get('ci_downloads_allowed') is False,
        'live_provider_calls_disabled': cfg.get('live_provider_calls_allowed') is False,
        'raw_csv_not_committed_default': cfg.get('commit_raw_csv') is False,
        'source_count_top5': len(sources) == 5,
        'all_sources_football_data': all(source.get('provider') == 'Football-Data.co.uk' for source in sources),
        'all_source_urls_declared': all(source.get('source_url', '').startswith('https://www.football-data.co.uk/') for source in sources),
        'all_raw_paths_under_local_historical': all(source.get('raw_csv', '').startswith('data/local_historical/football_data/raw/') for source in sources),
        'batch_002_row_target': targets.get('batch_002_target_min_rows') == 1000 and targets.get('batch_002_target_max_rows') == 3000,
        'baseline_eval_target': targets.get('minimum_rows_for_baseline_eval') == 250,
        'real_model_stays_locked': targets.get('real_model_ready_after_eval') is False,
        'aggregate_paths_declared': aggregate_paths.get('feature_counts_report') == 'reports/feature_counts.json' and aggregate_paths.get('model_eval_report') == 'reports/model_eval.json',
        'download_helper_added': (ROOT / 'scripts/download_football_data_batch_002.sh').exists(),
        'runner_added': (ROOT / 'scripts/run_football_data_batch_002.sh').exists(),
        'docs_added': (ROOT / 'docs/v991_football_data_batch_002.md').exists(),
    }

    data_checks = {
        'all_raw_csvs_present': all(raw_presence.values()),
        'all_normalized_matches_present': all(normalized_presence.values()),
        'aggregate_matches_present': aggregate_matches.exists(),
        'aggregate_odds_present': aggregate_odds.exists(),
        'feature_counts_present': feature_counts_path.exists(),
        'model_eval_present': model_eval_path.exists(),
    }

    generated_counts: Dict[str, Any] = {}
    generated_eval: Dict[str, Any] = {}
    if feature_counts_path.exists():
        generated_counts = read_json(feature_counts_path)
    if model_eval_path.exists():
        generated_eval = read_json(model_eval_path)

    aggregate_match_rows = count_jsonl(aggregate_matches)
    aggregate_odds_rows = count_jsonl(aggregate_odds)
    generated_ok = (
        aggregate_match_rows >= int(targets['batch_002_target_min_rows'])
        and generated_counts.get('schema') == 'omnibet.feature_count_gate.v921'
        and int(generated_counts.get('eligible_feature_rows', 0)) >= int(targets['batch_002_target_min_rows'])
        and generated_counts.get('real_model_ready') is False
        and generated_eval.get('schema') == 'omnibet.baseline_eval_report.v961'
        and generated_eval.get('real_model_ready') is False
    )

    if require_data:
        ok = all(manifest_checks.values()) and all(data_checks.values()) and generated_ok
        status = 'batch_002_ready' if ok else 'batch_002_blocked_or_incomplete'
    else:
        ok = all(manifest_checks.values())
        status = 'manifest_ready_waiting_for_local_raw_csvs'

    report = {
        'ok': ok,
        'schema': 'omnibet.football_data_batch_002_check.v991_v1030',
        'status': status,
        'require_data': require_data,
        'manifest_checks': manifest_checks,
        'raw_presence': raw_presence,
        'normalized_presence': normalized_presence,
        'data_checks': data_checks,
        'aggregate_match_rows': aggregate_match_rows,
        'aggregate_odds_rows': aggregate_odds_rows,
        'generated_counts': generated_counts,
        'generated_eval': generated_eval,
        'next_action': 'run scripts/download_football_data_batch_002.sh, then scripts/run_football_data_batch_002.sh' if not all(raw_presence.values()) else 'run scripts/run_football_data_batch_002.sh',
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-data', action='store_true', help='Require all raw/normalized data and generated reports.')
    parser.add_argument('--out', default='reports/ci_v991_v1030_football_data_batch_002.json')
    args = parser.parse_args()
    report = build_report(require_data=args.require_data)
    write_json(ROOT / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
