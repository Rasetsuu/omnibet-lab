#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python python_lab/v1031_football_data_batch_003_runner.py download
cat <<EOF
Football-Data Batch 003 download pass complete.

Some source files may be unavailable or skipped. The real acceptance gate is:
  bash scripts/run_football_data_batch_003.sh

That run must produce >=30,000 eligible rows.
EOF
