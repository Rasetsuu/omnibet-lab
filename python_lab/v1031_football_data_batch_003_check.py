#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'configs/football_data_batch_003.v1031_v1060.json'


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding='utf-8').splitlines() if line.strip())


def expected_source_count(cfg: Dict[str, Any]) -> int:
    return len(cfg.get('seasons', [])) * len(cfg.get('competitions', []))


def build_report(require_data: bool = False) -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH)
    targets = cfg['batch_targets']
    aggregate_paths = cfg['aggregate_paths']

    download_helper = ROOT / 'scripts/download_football_data_batch_003.sh'
    runner = ROOT / 'scripts/run_football_data_batch_003.sh'
    runner_py = ROOT / 'python_lab/v1031_football_data_batch_003_runner.py'
    docs = ROOT / 'docs/v1031_football_data_batch_003.md'
    workflow = ROOT / '.github/workflows/v1031_football_data_batch_003.yml'

    aggregate_matches = ROOT / aggregate_paths['matches_jsonl']
    aggregate_odds = ROOT / aggregate_paths['odds_jsonl']
    source_report_path = ROOT / aggregate_paths['source_report']
    feature_counts_path = ROOT / aggregate_paths['feature_counts_report']
    model_eval_path = ROOT / aggregate_paths['model_eval_report']

    manifest_checks = {
        'schema': cfg.get('schema') == 'omnibet.football_data_batch_003.v1031_v1060',
        'paper_only': cfg.get('paper_only') is True,
        'local_first': cfg.get('local_first') is True,
        'ci_downloads_disabled': cfg.get('ci_downloads_allowed') is False,
        'live_provider_calls_disabled': cfg.get('live_provider_calls_allowed') is False,
        'raw_csv_not_committed_default': cfg.get('commit_raw_csv') is False,
        'season_count': len(cfg.get('seasons', [])) >= 10,
        'competition_count': len(cfg.get('competitions', [])) >= 15,
        'source_grid_large_enough': expected_source_count(cfg) >= 150,
        'target_30k_declared': targets.get('batch_003_target_min_rows') == 30000,
        'real_model_stays_locked': targets.get('real_model_ready_after_eval') is False,
        'aggregate_reports_declared': aggregate_paths.get('feature_counts_report') == 'reports/feature_counts.json' and aggregate_paths.get('model_eval_report') == 'reports/model_eval.json',
        'download_helper_added': download_helper.exists(),
        'runner_added': runner.exists(),
        'runner_py_added': runner_py.exists(),
        'docs_added': docs.exists(),
        'workflow_added': workflow.exists(),
    }

    generated_counts: Dict[str, Any] = {}
    generated_eval: Dict[str, Any] = {}
    source_report: Dict[str, Any] = {}
    if feature_counts_path.exists():
        generated_counts = read_json(feature_counts_path)
    if model_eval_path.exists():
        generated_eval = read_json(model_eval_path)
    if source_report_path.exists():
        source_report = read_json(source_report_path)

    aggregate_match_rows = count_jsonl(aggregate_matches)
    aggregate_odds_rows = count_jsonl(aggregate_odds)
    data_checks = {
        'aggregate_matches_present': aggregate_matches.exists(),
        'aggregate_odds_present': aggregate_odds.exists(),
        'source_report_present': source_report_path.exists(),
        'feature_counts_present': feature_counts_path.exists(),
        'model_eval_present': model_eval_path.exists(),
        'aggregate_rows_30k_plus': aggregate_match_rows >= int(targets['batch_003_target_min_rows']),
        'feature_count_rows_30k_plus': int(generated_counts.get('eligible_feature_rows', 0)) >= int(targets['batch_003_target_min_rows']),
        'model_eval_generated': generated_eval.get('schema') == 'omnibet.baseline_eval_report.v961',
        'real_model_still_locked': generated_counts.get('real_model_ready') is False and generated_eval.get('real_model_ready') is False,
    }

    if require_data:
        ok = all(manifest_checks.values()) and all(data_checks.values())
        status = 'batch_003_ready_30k_plus' if ok else 'batch_003_blocked_or_incomplete'
    else:
        ok = all(manifest_checks.values())
        status = 'manifest_ready_waiting_for_local_30k_run'

    report = {
        'ok': ok,
        'schema': 'omnibet.football_data_batch_003_check.v1031_v1060',
        'status': status,
        'require_data': require_data,
        'expected_source_count': expected_source_count(cfg),
        'manifest_checks': manifest_checks,
        'data_checks': data_checks,
        'aggregate_match_rows': aggregate_match_rows,
        'aggregate_odds_rows': aggregate_odds_rows,
        'source_report': source_report,
        'generated_counts': generated_counts,
        'generated_eval': generated_eval,
        'next_action': 'run scripts/download_football_data_batch_003.sh, then scripts/run_football_data_batch_003.sh',
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-data', action='store_true', help='Require aggregate 30k+ data and generated reports.')
    parser.add_argument('--out', default='reports/ci_v1031_v1060_football_data_batch_003.json')
    args = parser.parse_args()
    report = build_report(require_data=args.require_data)
    write_json(ROOT / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
