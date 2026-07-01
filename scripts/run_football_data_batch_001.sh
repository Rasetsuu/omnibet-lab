#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RAW_CSV="data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv"
OUT_DIR="data/local_historical/football_data/normalized/england_premier_league/2024_2025"
FEATURE_COUNTS="reports/feature_counts.json"
SOURCE_URL="https://www.football-data.co.uk/mmz4281/2425/E0.csv"

if [[ ! -f "$RAW_CSV" ]]; then
  cat >&2 <<EOF
Football-Data Batch 001 is blocked because the raw CSV is not present.

Expected local file:
  $RAW_CSV

Download manually first:
  mkdir -p "$(dirname "$RAW_CSV")"
  curl -L "$SOURCE_URL" -o "$RAW_CSV"

Then rerun:
  bash scripts/run_football_data_batch_001.sh

This script intentionally does not download data automatically in CI.
EOF
  exit 2
fi

mkdir -p "$OUT_DIR" reports

cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-football-data-importer -- \
  --input "$RAW_CSV" \
  --competition england_premier_league \
  --season 2024_2025 \
  --out "$OUT_DIR"

cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-feature-count-gate -- \
  --matches "$OUT_DIR/matches.jsonl" \
  --out "$FEATURE_COUNTS" \
  --min-rows 200 \
  --source-label football_data_england_premier_league_2024_2025

python python_lab/v941_football_data_batch_001_check.py --require-data

cat <<EOF
Football-Data Batch 001 complete.

Generated:
  $OUT_DIR/matches.jsonl
  $OUT_DIR/odds.jsonl
  $OUT_DIR/import_report.json
  $FEATURE_COUNTS
EOF
