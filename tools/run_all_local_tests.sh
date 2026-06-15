#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p reports build data_packs

log() {
  printf '\n===== %s =====\n' "$*"
}

log "tool versions"
python --version
cargo --version
rustc --version

log "python compile"
(
  cd python_lab
  python -m py_compile *.py adapters/*.py
)

log "rebuild clean sqlite warehouse"
rm -f build/omnibet.sqlite build/omnibet.sqlite-wal build/omnibet.sqlite-shm
(
  cd python_lab
  python warehouse_manager.py init --db ../build/omnibet.sqlite | tee ../reports/ci_warehouse_init.json
  python -m adapters.football_data_uk_adapter \
    --db ../build/omnibet.sqlite \
    --input ../data/unified_intl_matches.csv \
    --competition unified_international \
    | tee ../reports/ci_football_data_import.json
  python gold_feature_builder.py build --db ../build/omnibet.sqlite | tee ../reports/ci_gold_build.json
  python export_data_pack.py \
    --db ../build/omnibet.sqlite \
    --out-dir ../data_packs/football_core_v1 \
    --pack-name football_core_v1 \
    | tee ../reports/ci_export_core_pack.json
  python verify_data_pack.py --pack-dir ../data_packs/football_core_v1 | tee ../reports/ci_verify_core_pack.json
)

log "synthetic event pipeline"
(
  cd python_lab
  python synthetic_event_demo.py \
    --base-db ../build/omnibet.sqlite \
    --demo-db ../build/omnibet_v13_event_demo.sqlite \
    --pack-dir ../data_packs/football_event_demo_v1 \
    --reports-dir ../reports \
    | tee ../reports/ci_synthetic_event_demo.json
  python verify_data_pack.py --pack-dir ../data_packs/football_event_demo_v1 | tee ../reports/ci_verify_event_demo_pack.json
)

log "StatsBomb public sample pipeline"
(
  cd python_lab
  python statsbomb_public_sample.py \
    --sample-root ../data/statsbomb_public_sample/data \
    --db ../build/omnibet_v14_statsbomb_sample.sqlite \
    --pack-dir ../data_packs/football_statsbomb_sample_v1 \
    --reports-dir ../reports \
    --limit-matches 12 \
    | tee ../reports/ci_statsbomb_public_sample.json
  python verify_data_pack.py --pack-dir ../data_packs/football_statsbomb_sample_v1 | tee ../reports/ci_verify_statsbomb_sample_pack.json
  python event_aware_compare.py \
    --db ../build/omnibet_v14_statsbomb_sample.sqlite \
    --out ../reports/ci_event_aware_compare.json \
    --require-event-rows 1 \
    | tee ../reports/ci_event_aware_compare_stdout.json
)

log "rust tests"
(
  cd rust-core
  cargo test
)

log "rust pack verify"
(
  cd rust-core
  cargo run --bin omnibet-pack -- verify ../data_packs/football_core_v1 | tee ../reports/ci_rust_pack_verify.json
  cargo run --bin omnibet-pack -- verify ../data_packs/football_event_demo_v1 | tee ../reports/ci_rust_event_pack_verify.json
  cargo run --bin omnibet-pack -- verify ../data_packs/football_statsbomb_sample_v1 | tee ../reports/ci_rust_statsbomb_pack_verify.json
)

log "rust model/runtime smoke"
(
  cd rust-core
  cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80 | tee ../reports/ci_rust_backtest.json
  cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1 80 | tee ../reports/ci_rust_backtest_gold.json
  cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80 | tee ../reports/ci_rust_compare.json
  cargo run --bin omnibet-model -- backtest \
    ../data_packs/football_statsbomb_sample_v1 \
    ../models/football_event_linear_v1.json \
    1 \
    | tee ../reports/ci_rust_event_linear_model.json
  cargo run --bin omnibet-value -- report \
    ../data_packs/football_core_v1 \
    Spain \
    "Cape Verde" \
    ../data/sample_odds_spain_cape_verde.csv \
    0.25 \
    | tee ../reports/ci_rust_value_report.json
)

log "paper ledger and CLV smoke"
(
  cd python_lab
  python paper_betting_ledger.py \
    --db ../build/omnibet.sqlite \
    --value-report ../reports/ci_rust_value_report.json \
    --closing-odds ../data/sample_closing_odds_spain_cape_verde.csv \
    --out ../reports/ci_paper_ledger.json \
    --fixture-id Spain-vs-Cape-Verde \
    | tee ../reports/ci_paper_ledger_stdout.json
)

log "collect CI summary"
python tools/collect_test_report.py --root "$ROOT" --out reports/ci_summary.json
cat reports/ci_summary.json

log "all checks passed"
