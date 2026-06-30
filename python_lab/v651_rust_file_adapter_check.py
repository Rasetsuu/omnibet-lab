#!/usr/bin/env python3
from pathlib import Path
import json

src = Path('rust-core/src/adapter_file_parsers_v651.rs').read_text(encoding='utf-8')
lib = Path('rust-core/src/lib.rs').read_text(encoding='utf-8')
checks = {
    'csv': 'parse_football_data_csv_v651' in src,
    'json_matches': 'parse_openfootball_json_v651' in src,
    'json_events': 'parse_statsbomb_events_json_v651' in src,
    'pack_builder': 'build_pack_from_sample_contents_v651' in src,
    'lib': 'adapter_file_parsers_v651' in lib,
    'tests': 'builds_pack_from_sample_contents_v651' in src,
}
report = {'ok': all(checks.values()), 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v651_rust_file_adapter_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
