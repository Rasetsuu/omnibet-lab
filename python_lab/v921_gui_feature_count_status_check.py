#!/usr/bin/env python3
from pathlib import Path
import json

ui = Path('tauri-app/src/simple_matches.js').read_text(encoding='utf-8')
doc = Path('docs/v921_rust_feature_count_gate.md').read_text(encoding='utf-8')
checks = {
    'fallback_row_count_preserved': '3 / 200 required for v1' in ui,
    'fallback_readiness_preserved': 'Needs more rows' in ui,
    'rust_report_loader': 'loadGeneratedFeatureCountStatus' in ui and 'feature_counts.json' in ui,
    'rust_report_fields': 'eligible_feature_rows' in ui and 'min_required_rows' in ui,
    'real_model_stays_locked': 'real_model_ready' in ui and 'Locked until walk-forward eval/calibration' in ui,
    'normal_controls_hidden': 'No training/import controls are exposed in the normal match screen' in ui,
    'docs_mentions_gui_fallback': 'GUI behavior' in doc and 'reports/feature_counts.json' in doc,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v921_gui_feature_count_status_check', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v921_gui_feature_count_status.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
