# v6 Commands

## Storage audit

```bash
cd python_lab
python storage_audit.py --root .. --db ../build/omnibet.sqlite --out ../reports/v6_storage_audit.json
```

## Export compressed pack

```bash
python export_data_pack.py \
  --db ../build/omnibet.sqlite \
  --out-dir ../data_packs/football_core_v1 \
  --pack-name football_core_v1
```

## Verify pack

```bash
python verify_data_pack.py --pack-dir ../data_packs/football_core_v1
```

## Rust core

If Rust is installed:

```bash
cd rust-core
cargo test
cargo run --bin omnibet-core
```

In this environment Rust may not be installed; that is okay for the v6 artifact.
