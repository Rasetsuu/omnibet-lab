#!/usr/bin/env python3
from pathlib import Path
import json

bin_rs = Path('rust-core/src/bin/omnibet-sample-pack-runner.rs').read_text(encoding='utf-8')
cargo = Path('rust-core/Cargo.toml').read_text(encoding='utf-8')
cfg = json.loads(Path('configs/rust_sample_runner.v681_v710.json').read_text(encoding='utf-8'))
checks = {
    'schema': cfg.get('schema') == 'omnibet.rust_sample_runner_contract.v681_v710',
    'runner': 'build_pack_from_sample_contents_v651' in bin_rs,
    'default_csv': 'football_data_sample.csv' in bin_rs,
    'default_json': 'openfootball_sample.json' in bin_rs,
    'default_events': 'statsbomb_events_sample.json' in bin_rs,
    'report': 'rust_sample_pack_v681_v710.json' in bin_rs,
    'cargo_bin': 'omnibet-sample-pack-runner' in cargo,
}
report = {'ok': all(checks.values()), 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v681_rust_sample_runner_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
