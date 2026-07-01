#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AGG_DIR="data/local_historical/football_data/normalized/batch_002_top5_2024_2025"
AGG_MATCHES="$AGG_DIR/matches.jsonl"
AGG_ODDS="$AGG_DIR/odds.jsonl"

check_raw() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "missing raw CSV: $path" >&2
    return 1
  fi
}

missing=0
check_raw "data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv" || missing=1
check_raw "data/local_historical/football_data/raw/spain_la_liga/2024_2025/SP1.csv" || missing=1
check_raw "data/local_historical/football_data/raw/italy_serie_a/2024_2025/I1.csv" || missing=1
check_raw "data/local_historical/football_data/raw/germany_bundesliga/2024_2025/D1.csv" || missing=1
check_raw "data/local_historical/football_data/raw/france_ligue_1/2024_2025/F1.csv" || missing=1

if [[ "$missing" -ne 0 ]]; then
  cat >&2 <<EOF
Football-Data Batch 002 is blocked because one or more raw CSVs are missing.

Fetch them with:
  bash scripts/download_football_data_batch_002.sh

Then rerun:
  bash scripts/run_football_data_batch_002.sh
EOF
  exit 2
fi

run_import() {
  local input="$1"
  local competition="$2"
  local season="$3"
  local out="$4"
  mkdir -p "$out"
  cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-football-data-importer -- \
    --input "$input" \
    --competition "$competition" \
    --season "$season" \
    --out "$out"
}

run_import "data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv" "england_premier_league" "2024_2025" "data/local_historical/football_data/normalized/england_premier_league/2024_2025"
run_import "data/local_historical/football_data/raw/spain_la_liga/2024_2025/SP1.csv" "spain_la_liga" "2024_2025" "data/local_historical/football_data/normalized/spain_la_liga/2024_2025"
run_import "data/local_historical/football_data/raw/italy_serie_a/2024_2025/I1.csv" "italy_serie_a" "2024_2025" "data/local_historical/football_data/normalized/italy_serie_a/2024_2025"
run_import "data/local_historical/football_data/raw/germany_bundesliga/2024_2025/D1.csv" "germany_bundesliga" "2024_2025" "data/local_historical/football_data/normalized/germany_bundesliga/2024_2025"
run_import "data/local_historical/football_data/raw/france_ligue_1/2024_2025/F1.csv" "france_ligue_1" "2024_2025" "data/local_historical/football_data/normalized/france_ligue_1/2024_2025"

mkdir -p "$AGG_DIR" reports
: > "$AGG_MATCHES"
: > "$AGG_ODDS"
cat data/local_historical/football_data/normalized/england_premier_league/2024_2025/matches.jsonl >> "$AGG_MATCHES"
cat data/local_historical/football_data/normalized/spain_la_liga/2024_2025/matches.jsonl >> "$AGG_MATCHES"
cat data/local_historical/football_data/normalized/italy_serie_a/2024_2025/matches.jsonl >> "$AGG_MATCHES"
cat data/local_historical/football_data/normalized/germany_bundesliga/2024_2025/matches.jsonl >> "$AGG_MATCHES"
cat data/local_historical/football_data/normalized/france_ligue_1/2024_2025/matches.jsonl >> "$AGG_MATCHES"
cat data/local_historical/football_data/normalized/england_premier_league/2024_2025/odds.jsonl >> "$AGG_ODDS"
cat data/local_historical/football_data/normalized/spain_la_liga/2024_2025/odds.jsonl >> "$AGG_ODDS"
cat data/local_historical/football_data/normalized/italy_serie_a/2024_2025/odds.jsonl >> "$AGG_ODDS"
cat data/local_historical/football_data/normalized/germany_bundesliga/2024_2025/odds.jsonl >> "$AGG_ODDS"
cat data/local_historical/football_data/normalized/france_ligue_1/2024_2025/odds.jsonl >> "$AGG_ODDS"

cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-feature-count-gate -- \
  --matches "$AGG_MATCHES" \
  --out reports/feature_counts.json \
  --min-rows 200 \
  --source-label football_data_batch_002_top5_2024_2025

cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-baseline-eval -- \
  --matches "$AGG_MATCHES" \
  --out reports/model_eval.json \
  --min-train 200 \
  --min-eval 50 \
  --eval-fraction 0.20 \
  --source-label football_data_batch_002_top5_2024_2025

python python_lab/v991_football_data_batch_002_check.py --require-data

cat <<EOF
Football-Data Batch 002 complete.

Generated:
  $AGG_MATCHES
  $AGG_ODDS
  reports/feature_counts.json
  reports/model_eval.json
EOF
