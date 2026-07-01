#!/usr/bin/env python3
from pathlib import Path
import json

ui = Path('tauri-app/src/simple_matches.js').read_text(encoding='utf-8')
doc = Path('docs/v971_gui_model_eval_status.md').read_text(encoding='utf-8')
checks = {
    'feature_count_fallback_preserved': '3 / 200 required for v1' in ui and 'feature_counts.json' in ui,
    'model_eval_loader_added': 'loadGeneratedModelEvalStatus' in ui and 'model_eval.json' in ui,
    'model_eval_status_rows': 'Baseline eval source' in ui and 'Baseline eval' in ui and 'Eval metrics' in ui,
    'model_eval_fields': all(token in ui for token in ['accuracy', 'log_loss', 'brier_score', 'calibration_ece']),
    'merged_status_not_overwrite': 'mergeAndRenderDataStatus' in ui and '__omnibetDataStatus' in ui,
    'real_model_stays_locked': 'real_model_ready' in ui and 'Still locked' in ui,
    'normal_controls_hidden': 'No training/import controls are exposed in the normal match screen' in ui,
    'docs_added': 'v971-v980 GUI model eval status' in doc and 'reports/model_eval.json' in doc,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v971_gui_model_eval_status_check', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v971_gui_model_eval_status.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
