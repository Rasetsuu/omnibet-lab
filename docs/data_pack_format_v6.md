# OmniBet Data Pack Format v6

v6 introduces a first compressed data-pack format.

## Layout

```text
data_packs/
  football_core_v1/
    manifest.json
    tables/
      matches_norm.jsonl.gz
      gold_match_features.jsonl.gz
      gold_team_snapshots.jsonl.gz
      ...
```

## Manifest fields

- pack name
- sport
- format version
- created time
- source database
- storage policy
- table list
- rows
- uncompressed JSONL bytes
- compressed bytes
- compression ratio
- SHA256 per table
- schema per table

## Commands

```bash
cd python_lab

python storage_audit.py --root .. --db ../build/omnibet.sqlite
python export_data_pack.py --db ../build/omnibet.sqlite --out-dir ../data_packs/football_core_v1
python verify_data_pack.py --pack-dir ../data_packs/football_core_v1
```

## Final target

The final Rust engine should read validated packs directly or through a compact index layer.
