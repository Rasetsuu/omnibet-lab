#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'configs/football_data_batch_003.v1031_v1060.json'


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def source_rows(cfg: Dict[str, Any]) -> Iterable[Dict[str, str]]:
    for season in cfg['seasons']:
        season_id = cfg['season_ids'][season]
        for comp in cfg['competitions']:
            code = comp['code']
            competition_id = comp['competition_id']
            yield {
                'season': season,
                'season_id': season_id,
                'code': code,
                'competition_id': competition_id,
                'country': comp['country'],
                'url': cfg['url_template'].format(season=season, code=code),
                'raw_csv': cfg['raw_path_template'].format(competition_id=competition_id, season_id=season_id, code=code),
                'normalized_dir': cfg['normalized_path_template'].format(competition_id=competition_id, season_id=season_id),
            }


def run(cmd: List[str]) -> None:
    print('+ ' + ' '.join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def download(cfg: Dict[str, Any]) -> Dict[str, Any]:
    attempted = 0
    downloaded = 0
    already_present = 0
    failed: List[Dict[str, str]] = []
    for row in source_rows(cfg):
        attempted += 1
        out = ROOT / row['raw_csv']
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and out.stat().st_size > 0:
            already_present += 1
            print(f'exists: {row["raw_csv"]}')
            continue
        try:
            print(f'download: {row["url"]} -> {row["raw_csv"]}')
            with urllib.request.urlopen(row['url'], timeout=30) as response:
                data = response.read()
            if len(data) < 100 or b'404' in data[:200].lower():
                raise RuntimeError('downloaded payload looked invalid or too small')
            out.write_bytes(data)
            downloaded += 1
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
            failed.append({'url': row['url'], 'raw_csv': row['raw_csv'], 'error': str(exc)})
            print(f'warn: failed {row["url"]}: {exc}')
    report = {
        'schema': 'omnibet.football_data_batch_003_download.v1031_v1060',
        'attempted': attempted,
        'downloaded': downloaded,
        'already_present': already_present,
        'failed_count': len(failed),
        'failed': failed[:50],
        'note': 'Some missing files are acceptable; the final data gate requires aggregate 30k+ eligible rows.',
    }
    write_json(ROOT / 'reports/ci_v1031_v1060_football_data_batch_003_download.json', report)
    return report


def concat_files(paths: Iterable[Path], out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open('w', encoding='utf-8') as dst:
        for path in paths:
            if not path.exists():
                continue
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    dst.write(line)
                    dst.write('\n')
                    count += 1
    return count


def run_batch(cfg: Dict[str, Any]) -> Dict[str, Any]:
    imported = []
    skipped_missing = []
    for row in source_rows(cfg):
        raw = ROOT / row['raw_csv']
        if not raw.exists():
            skipped_missing.append(row)
            continue
        out_dir = ROOT / row['normalized_dir']
        out_dir.mkdir(parents=True, exist_ok=True)
        run([
            'cargo', 'run', '--manifest-path', 'rust-core/Cargo.toml', '--bin', 'omnibet-football-data-importer', '--',
            '--input', row['raw_csv'],
            '--competition', row['competition_id'],
            '--season', row['season_id'],
            '--out', row['normalized_dir'],
        ])
        imported.append(row)

    aggregate = cfg['aggregate_paths']
    agg_dir = ROOT / aggregate['normalized_dir']
    agg_matches = ROOT / aggregate['matches_jsonl']
    agg_odds = ROOT / aggregate['odds_jsonl']
    match_paths = [ROOT / row['normalized_dir'] / 'matches.jsonl' for row in imported]
    odds_paths = [ROOT / row['normalized_dir'] / 'odds.jsonl' for row in imported]
    match_rows = concat_files(match_paths, agg_matches)
    odds_rows = concat_files(odds_paths, agg_odds)

    source_report = {
        'schema': 'omnibet.football_data_batch_003_source_report.v1031_v1060',
        'declared_sources': len(list(source_rows(cfg))),
        'imported_sources': len(imported),
        'skipped_missing_sources': len(skipped_missing),
        'aggregate_match_rows': match_rows,
        'aggregate_odds_rows': odds_rows,
        'target_min_rows': cfg['batch_targets']['batch_003_target_min_rows'],
        'imported': imported,
        'skipped_missing': skipped_missing[:100],
    }
    write_json(ROOT / aggregate['source_report'], source_report)

    run([
        'cargo', 'run', '--manifest-path', 'rust-core/Cargo.toml', '--bin', 'omnibet-feature-count-gate', '--',
        '--matches', aggregate['matches_jsonl'],
        '--out', aggregate['feature_counts_report'],
        '--min-rows', '200',
        '--source-label', 'football_data_batch_003_multi_season_30k',
    ])
    run([
        'cargo', 'run', '--manifest-path', 'rust-core/Cargo.toml', '--bin', 'omnibet-baseline-eval', '--',
        '--matches', aggregate['matches_jsonl'],
        '--out', aggregate['model_eval_report'],
        '--min-train', '200',
        '--min-eval', '50',
        '--eval-fraction', '0.20',
        '--source-label', 'football_data_batch_003_multi_season_30k',
    ])
    run(['python', 'python_lab/v1031_football_data_batch_003_check.py', '--require-data'])
    return source_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['download', 'run'])
    args = parser.parse_args()
    cfg = read_json(CONFIG_PATH)
    if args.mode == 'download':
        report = download(cfg)
    else:
        report = run_batch(cfg)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
