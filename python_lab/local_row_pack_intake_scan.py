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


def count_csv_rows(path: Path) -> int:
    with path.open(newline='', encoding='utf-8') as handle:
        return sum(1 for _ in csv.DictReader(handle))


def count_json_rows(path: Path) -> int:
    payload = read_json(path)
    if isinstance(payload.get('matches'), list):
        return len(payload['matches'])
    if isinstance(payload.get('events'), list):
        return len(payload['events'])
    if isinstance(payload.get('fixtures'), list):
        return len(payload['fixtures'])
    if isinstance(payload.get('settlements'), list):
        return len(payload['settlements'])
    return 0


def scan_dir(root: Path, folder: Path, accepted: set[str]) -> List[Dict[str, Any]]:
    if not folder.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in accepted:
            continue
        if path.suffix.lower() == '.csv':
            row_count = count_csv_rows(path)
            shape = 'csv_match_rows'
        else:
            row_count = count_json_rows(path)
            shape = 'json_rows'
        rows.append({
            'path': str(path.relative_to(root)),
            'extension': path.suffix.lower(),
            'shape': shape,
            'row_count': row_count,
        })
    return rows


def build_report(root: Path) -> Dict[str, Any]:
    cfg = read_json(root / 'configs/local_row_pack_intake.v771_v800.json')
    accepted = set(cfg['accepted_extensions'])
    folders = [Path(cfg['intake_dir'])] + [Path(p) for p in cfg.get('sample_dirs', [])]
    files: List[Dict[str, Any]] = []
    for folder in folders:
        files.extend(scan_dir(root, root / folder, accepted))
    total_rows = sum(row['row_count'] for row in files)
    thresholds = cfg['thresholds']
    scan = {
        'schema': 'omnibet.local_row_pack_scan.v771_v800',
        'files': files,
        'counts': {
            'files': len(files),
            'rows': total_rows,
        },
        'gate': {
            'preview_count_ok': total_rows >= thresholds['minimum_rows_for_gate_preview'],
            'v1_baseline_count_ok': total_rows >= thresholds['minimum_rows_for_v1_baseline'],
            'minimum_rows_for_v1_baseline': thresholds['minimum_rows_for_v1_baseline'],
        },
        'status': 'needs_more_rows_for_v1_baseline' if total_rows < thresholds['minimum_rows_for_v1_baseline'] else 'row_count_ready_for_v1_baseline',
    }
    write_json(root / cfg['outputs']['scan_report'], scan)
    checks = {
        'schema': cfg.get('schema') == 'omnibet.local_row_pack_intake.v771_v800',
        'intake_readme': (root / 'data/local_historical/README.md').exists(),
        'found_sample_files': len(files) >= 3,
        'sample_rows_available': total_rows >= thresholds['minimum_rows_for_gate_preview'],
        'v1_not_ready_yet': total_rows < thresholds['minimum_rows_for_v1_baseline'],
        'scan_report_written': (root / cfg['outputs']['scan_report']).exists(),
    }
    return {
        'ok': all(checks.values()),
        'schema': 'omnibet.local_row_pack_intake_smoke.v771_v800',
        'checks': checks,
        'summary': scan['counts'],
        'status': scan['status'],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--out', default='reports/ci_v771_v800_local_row_pack_intake.json')
    args = parser.parse_args()
    root = Path(args.root)
    report = build_report(root)
    write_json(root / args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
