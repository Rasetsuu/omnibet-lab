#!/usr/bin/env python3
from pathlib import Path
import json

src = Path('rust-core/src/adapter_normalizer_v621.rs').read_text(encoding='utf-8')
lib = Path('rust-core/src/lib.rs').read_text(encoding='utf-8')
checks = {
    'fixture': 'NormalizedFixtureRowV621' in src,
    'result': 'NormalizedResultRowV621' in src,
    'event': 'NormalizedEventRowV621' in src,
    'pack': 'NormalizedHistoricalPackV621' in src,
    'validate': 'validate_normalized_pack_v621' in src,
    'lib': 'adapter_normalizer_v621' in lib,
}
report = {'ok': all(checks.values()), 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v621_rust_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
