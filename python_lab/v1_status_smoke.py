#!/usr/bin/env python3
from pathlib import Path
import json

cfg = json.loads(Path('configs/v1_status.v741_v770.json').read_text(encoding='utf-8'))
doc = Path('docs/v1_roadmap_status.md').read_text(encoding='utf-8')
checks = {
    'schema': cfg.get('schema') == 'omnibet.v1_status.v741_v770',
    'paper_target': cfg.get('paper_only_target') is True,
    'progress': cfg.get('paper_v1_progress_estimate') == 40,
    'not_trained_good': cfg.get('current_good_training') is False,
    'remaining': 'feature_builder_v1' in cfg.get('remaining_to_v1', []),
    'doc_status': 'OmniBet is not trained well yet.' in doc,
    'doc_finish_line': 'first meaningful v1.0' in doc,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v1_status_smoke.v741_v770', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v1_status_v741_v770.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
