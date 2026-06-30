#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys

cfg = json.loads(Path('configs/v831_counts.json').read_text(encoding='utf-8'))
subprocess.run([sys.executable, cfg['input_script']], check=True)
rows_payload = json.loads(Path(cfg['input_rows']).read_text(encoding='utf-8'))
row_count = int(rows_payload.get('row_count', len(rows_payload.get('rows', []))))
minimum = int(cfg['minimum_rows'])
report = {
    'schema': 'omnibet.v831_counts_report',
    'ok': True,
    'row_count': row_count,
    'minimum_rows': minimum,
    'ready': row_count >= minimum,
    'status': 'ready' if row_count >= minimum else 'needs_more_rows',
}
Path('reports').mkdir(exist_ok=True)
Path(cfg['output_report']).write_text(json.dumps(report, indent=2), encoding='utf-8')
ci = {
    'ok': row_count == int(cfg['expected_rows_now']) and report['ready'] is False,
    'schema': 'omnibet.v831_counts_ci',
    'report': report,
}
Path('reports/ci_v831_counts.json').write_text(json.dumps(ci, indent=2), encoding='utf-8')
print(json.dumps(ci, indent=2))
if not ci['ok']:
    raise SystemExit(1)
