#!/usr/bin/env python3
from pathlib import Path
import json

workflow = Path('.github/workflows/desktop_release.yml').read_text(encoding='utf-8')
run002 = Path('scripts/run_football_data_batch_002.sh').read_text(encoding='utf-8')
runner003 = Path('python_lab/v1031_football_data_batch_003_runner.py').read_text(encoding='utf-8')
doc = Path('docs/desktop_release_data_batches_v200_followup.md').read_text(encoding='utf-8')
checks = {
    'release_bundles_scripts_dir': '"$package_dir/scripts"' in workflow,
    'release_bundles_python_lab_dir': '"$package_dir/python_lab"' in workflow,
    'release_bundles_new_rust_clis': all(token in workflow for token in ['omnibet-football-data-importer', 'omnibet-feature-count-gate', 'omnibet-baseline-eval']),
    'release_bundles_batch_scripts': all(token in workflow for token in ['download_football_data_batch_002.sh', 'run_football_data_batch_002.sh', 'download_football_data_batch_003.sh', 'run_football_data_batch_003.sh']),
    'release_bundles_batch_configs': all(token in workflow for token in ['football_data_batch_002.v991_v1030.json', 'football_data_batch_003.v1031_v1060.json']),
    'release_bundles_python_checks': all(token in workflow for token in ['v991_football_data_batch_002_check.py', 'v1031_football_data_batch_003_check.py', 'v1031_football_data_batch_003_runner.py']),
    'batch002_prefers_bundled_cli': 'run_cli_or_cargo' in run002 and '$ROOT/bin/' in run002,
    'batch003_prefers_bundled_cli': 'run_cli_or_cargo' in runner003 and "ROOT / 'bin'" in runner003,
    'docs_added': 'Desktop release data-batch packaging follow-up' in doc,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v200_desktop_release_data_batch_packaging_check', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v200_desktop_release_data_batch_packaging.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
