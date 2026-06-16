#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p reports build data_packs build/models

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

log "market registry phase scope"
(
  cd python_lab
  python market_registry.py --sport football --json ../reports/ci_market_registry_football.json | tee ../reports/ci_market_registry_football_stdout.json
)

log "UI wiring check"
python tools/check_ui_wiring.py --root "$ROOT" --out reports/ci_ui_wiring.json

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

log "v20 data-scale smoke + v21 phase lab + v22 training export + v24 walk-forward"
(
  cd python_lab
  python statsbomb_scale_pipeline.py \
    --profile smoke \
    --sample-root ../data/statsbomb_scale_sample/data \
    --db ../build/omnibet_v20_statsbomb_scale.sqlite \
    --pack-dir ../data_packs/football_statsbomb_scale_v1 \
    --pack-name football_statsbomb_scale_v1 \
    --reports-dir ../reports \
    --report-name ci_v20_data_scale.json \
    --max-matches 16 \
    | tee ../reports/ci_v20_data_scale_stdout.json
  python football_phase_lab.py \
    --db ../build/omnibet_v20_statsbomb_scale.sqlite \
    --out ../reports/ci_v21_phase_lab.json \
    | tee ../reports/ci_v21_phase_lab_stdout.json
  python train_linear_model.py \
    --db ../build/omnibet_v20_statsbomb_scale.sqlite \
    --out-model ../build/models/football_regulation_linear_trained_v1.json \
    --out-report ../reports/ci_v22_train_export.json \
    --model-trust 0.35 \
    | tee ../reports/ci_v22_train_export_stdout.json
  python walk_forward_backtest.py \
    --db ../build/omnibet_v20_statsbomb_scale.sqlite \
    --out ../reports/ci_v24_walk_forward.json \
    --min-train 6 \
    --min-test-rows 4 \
    --model-trust 0.35 \
    | tee ../reports/ci_v24_walk_forward_stdout.json
  python export_data_pack.py \
    --db ../build/omnibet_v20_statsbomb_scale.sqlite \
    --out-dir ../data_packs/football_phase_training_v1 \
    --pack-name football_phase_training_v1 \
    | tee ../reports/ci_export_phase_training_pack.json
  python verify_data_pack.py --pack-dir ../data_packs/football_statsbomb_scale_v1 | tee ../reports/ci_verify_statsbomb_scale_pack.json
  python verify_data_pack.py --pack-dir ../data_packs/football_phase_training_v1 | tee ../reports/ci_verify_phase_training_pack.json
)

log "v23 multi-source adapter smoke + v25 odds CLV walk-forward"
(
  cd python_lab
  python multisource_lab.py \
    --db ../build/omnibet_v23_multisource.sqlite \
    --football-data-csv ../data/samples/football_data_odds_sample.csv \
    --openfootball-json ../data/samples/openfootball_sample.json \
    --wyscout-matches ../data/samples/wyscout_public_sample_matches.json \
    --wyscout-events ../data/samples/wyscout_public_sample_events.json \
    --pack-dir ../data_packs/football_multisource_v1 \
    --pack-name football_multisource_v1 \
    --out ../reports/ci_v23_multisource.json \
    | tee ../reports/ci_v23_multisource_stdout.json
  python odds_walk_forward_backtest.py \
    --db ../build/omnibet_v23_multisource.sqlite \
    --out ../reports/ci_v25_odds_clv_backtest.json \
    --min-train 1 \
    --min-bets 1 \
    --min-edge 0.0 \
    | tee ../reports/ci_v25_odds_clv_backtest_stdout.json
  python verify_data_pack.py --pack-dir ../data_packs/football_multisource_v1 | tee ../reports/ci_verify_multisource_pack.json
)

log "v26 local backfill tiny smoke"
(
  cd python_lab
  python local_backfill_runner.py \
    --preset tiny-smoke \
    --out ../build/v26_smoke \
    --pack-name football_v26_tiny_smoke \
    | tee ../reports/ci_v26_local_backfill.json
  python verify_data_pack.py \
    --pack-dir ../build/v26_smoke/packs/football_v26_tiny_smoke \
    | tee ../reports/ci_verify_v26_backfill_pack.json
)

log "v27 Parquet+ZSTD storage plan"
(
  cd python_lab
  python export_parquet_zstd_pack.py \
    --plan-only \
    --db ../build/v26_smoke/omnibet_v26_backfill.sqlite \
    --out ../reports/ci_v27_parquet_zstd_plan.json \
    | tee ../reports/ci_v27_parquet_zstd_plan_stdout.json
)

log "v28 real-source acquisition catalog"
(
  cd python_lab
  python source_acquisition_catalog.py \
    --out ../reports/ci_v28_source_catalog.json \
    --write-example-config ../configs/source_acquisition.v28.example.json \
    --write-shell-plan ../build/v28_sync_sources_plan.sh \
    | tee ../reports/ci_v28_source_catalog_stdout.json
)

log "v29 feature priority and live data contract"
(
  cd python_lab
  python feature_live_contract.py \
    --out ../reports/ci_v29_feature_live_contract.json \
    --write-config ../configs/feature_live_contract.v29.json \
    | tee ../reports/ci_v29_feature_live_contract_stdout.json
)

log "v30 bookmaker odds and bet builder market contract"
(
  cd python_lab
  python bookmaker_market_contract.py \
    --out ../reports/ci_v30_bookmaker_market_contract.json \
    --write-config ../configs/bookmaker_market_contract.v30.json \
    | tee ../reports/ci_v30_bookmaker_market_contract_stdout.json
)

log "v31 provider matrix and market discovery schema"
(
  cd python_lab
  python provider_market_discovery.py \
    --out ../reports/ci_v31_provider_market_discovery.json \
    --write-config ../configs/provider_market_discovery.v31.json \
    | tee ../reports/ci_v31_provider_market_discovery_stdout.json
)

log "v32 raw market snapshot warehouse smoke"
(
  cd python_lab
  python market_snapshot_smoke.py \
    --db ../build/omnibet_v32_market_smoke.sqlite \
    --out ../reports/ci_v32_market_snapshot_smoke.json \
    | tee ../reports/ci_v32_market_snapshot_smoke_stdout.json
)

log "v33 canonical resolver smoke"
(
  cd python_lab
  python canonical_resolver_smoke.py \
    --db ../build/omnibet_v33_resolver_smoke.sqlite \
    --out ../reports/ci_v33_canonical_resolver_smoke.json \
    | tee ../reports/ci_v33_canonical_resolver_smoke_stdout.json
)

log "v34 market alias apply smoke"
(
  cd python_lab
  python market_alias_apply_smoke.py \
    --db ../build/omnibet_v34_market_alias_apply.sqlite \
    --out ../reports/ci_v34_market_alias_apply.json \
    | tee ../reports/ci_v34_market_alias_apply_stdout.json
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
  cargo run --bin omnibet-pack -- verify ../data_packs/football_statsbomb_scale_v1 | tee ../reports/ci_rust_statsbomb_scale_pack_verify.json
  cargo run --bin omnibet-pack -- verify ../data_packs/football_phase_training_v1 | tee ../reports/ci_rust_phase_training_pack_verify.json
  cargo run --bin omnibet-pack -- verify ../data_packs/football_multisource_v1 | tee ../reports/ci_rust_multisource_pack_verify.json
  cargo run --bin omnibet-pack -- verify ../build/v26_smoke/packs/football_v26_tiny_smoke | tee ../reports/ci_rust_v26_backfill_pack_verify.json
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
  cargo run --bin omnibet-model -- backtest \
    ../data_packs/football_phase_training_v1 \
    ../build/models/football_regulation_linear_trained_v1.json \
    1 \
    | tee ../reports/ci_rust_trained_model.json
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
