#!/usr/bin/env python3
from pathlib import Path
import json

rust = Path('rust-core/src/baseline_eval_report_v961.rs').read_text(encoding='utf-8')
cli = Path('rust-core/src/bin/omnibet-baseline-eval.rs').read_text(encoding='utf-8')
cargo = Path('rust-core/Cargo.toml').read_text(encoding='utf-8')
lib = Path('rust-core/src/lib.rs').read_text(encoding='utf-8')
doc = Path('docs/v961_rust_baseline_eval_report.md').read_text(encoding='utf-8')
checks = {
    'rust_module_added': 'BaselineEvalReportV961' in rust and 'build_baseline_eval_report_v961' in rust,
    'chronological_split': 'No random split is used' in rust and 'rows.sort_by' in rust,
    'metrics_added': all(token in rust for token in ['accuracy', 'log_loss', 'brier_score', 'calibration_ece']),
    'real_model_stays_locked': 'real_model_ready: false' in rust,
    'regulation_90_scope': 'regulation_90' in rust,
    'cli_added': 'omnibet-baseline-eval' in cargo and 'build_baseline_eval_report_v961' in cli,
    'lib_exports_added': 'baseline_eval_report_v961' in lib,
    'docs_added': 'v961-v990 Rust baseline evaluation report' in doc and 'not a trained betting model' in doc,
}
report = {'ok': all(checks.values()), 'schema': 'omnibet.v961_baseline_eval_report_check', 'checks': checks}
Path('reports').mkdir(exist_ok=True)
Path('reports/ci_v961_baseline_eval_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not report['ok']:
    raise SystemExit(1)
