#!/usr/bin/env python3
from pathlib import Path
import json
import re

ui = Path('tauri-app/src/simple_matches.js').read_text(encoding='utf-8')
cfg = json.loads(Path('configs/gui_data_status_panel.v711_v740.json').read_text(encoding='utf-8'))
required = cfg['required_labels']
checks = {
    'schema': cfg.get('schema') == 'omnibet.gui_data_status_panel_contract.v711_v740',
    'panel_id': 'matches-data-status' in ui,
    'renderer': re.search(r'function\s+renderDataStatus\s*\(', ui) is not None,
    'called': 'renderDataStatus(' in ui or 'renderDataStatus();' in ui,
    'labels': all(label in ui for label in required),
    'no_training_button': 'id="matches-train' not in ui and 'id="matches-import' not in ui,
    'passive_text': 'Status only' in ui,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.gui_data_status_panel_smoke.v711_v740', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v711_v740_gui_data_status_panel.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
