#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fetch_csv() {
  local url="$1"
  local out="$2"
  mkdir -p "$(dirname "$out")"
  if [[ -f "$out" ]]; then
    echo "exists: $out"
    return 0
  fi
  echo "download: $url -> $out"
  curl -L "$url" -o "$out"
}

fetch_csv "https://www.football-data.co.uk/mmz4281/2425/E0.csv" "data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv"
fetch_csv "https://www.football-data.co.uk/mmz4281/2425/SP1.csv" "data/local_historical/football_data/raw/spain_la_liga/2024_2025/SP1.csv"
fetch_csv "https://www.football-data.co.uk/mmz4281/2425/I1.csv" "data/local_historical/football_data/raw/italy_serie_a/2024_2025/I1.csv"
fetch_csv "https://www.football-data.co.uk/mmz4281/2425/D1.csv" "data/local_historical/football_data/raw/germany_bundesliga/2024_2025/D1.csv"
fetch_csv "https://www.football-data.co.uk/mmz4281/2425/F1.csv" "data/local_historical/football_data/raw/france_ligue_1/2024_2025/F1.csv"

cat <<EOF
Football-Data Batch 002 raw CSVs are present.

Next:
  bash scripts/run_football_data_batch_002.sh
EOF
