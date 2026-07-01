#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python python_lab/v1031_football_data_batch_003_runner.py run
cat <<EOF
Football-Data Batch 003 complete.

Generated:
  data/local_historical/football_data/normalized/batch_003_multi_season_30k/matches.jsonl
  data/local_historical/football_data/normalized/batch_003_multi_season_30k/odds.jsonl
  reports/feature_counts.json
  reports/model_eval.json
EOF
