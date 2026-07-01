#!/usr/bin/env python3
from pathlib import Path
import json

ui = Path('tauri-app/src/simple_matches.js').read_text(encoding='utf-8')
checks = {
    'row_count_visible': 'Completed row count' in ui and '3 / 200 required for v1' in ui,
    'v1_status_visible': 'V1 readiness' in ui and 'Needs more rows' in ui,
    'status_panel': 'matches-data-status' in ui,
    'status_only_text': 'Status only' in ui,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v861_gui_counts_status_check', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v861_gui_counts_status.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
