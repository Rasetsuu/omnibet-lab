# v311-v320 Rust Storage V2 Writers and Compression

This batched phase starts the concrete Python-to-Rust migration for stable storage paths.

It implements Rust preview writers for:

```text
JSONL.Zstd raw snapshot tables
JSON.Zstd raw payload archives
JSONL.Gzip small CI/runtime compatibility tables
```

It also adds manifest writers and validation hooks for:

```text
Silver Parquet.Zstd tables
Gold Parquet.Zstd feature tables
```

Parquet.Zstd remains manifest-only in this phase because real table schemas must be locked before the heavy table writer is introduced.

## Included versions

```text
v311 JSONL.Zstd raw snapshot writer
v312 JSON.Zstd raw payload writer
v313 provider cache manifest writer
v314 Bronze manifest verification
v315 Silver table manifest writer
v316 Gold feature manifest writer
v317 row counts and content hashes
v318 retention/delete-after-promotion gates
v319 local storage writer smoke
v320 desktop storage writer status panel
```

## Real Rust implementation now

The Rust module lives in:

```text
rust-core/src/storage_v2_writers_v311.rs
```

It provides:

```text
write_jsonl_zstd_table
write_json_zstd_payload
write_jsonl_gzip_table
build_parquet_zstd_manifest_only
build_bundle_manifest
verify_storage_writer_bundle
retention_gate_decision
validate_storage_v2_writers_contract
```

## Codec split

Implemented now:

```text
jsonl.zstd
json.zstd
jsonl.gzip
```

Manifest-only now:

```text
parquet.zstd
```

`jsonl.gzip` stays because small CI/runtime packs already rely on it. `jsonl.zstd` and `json.zstd` are the forward path for temporary Bronze raw snapshots and payloads. `parquet.zstd` remains the long-term target for Silver/Gold tables.

## Retention gates

Bronze raw data may only be deleted when all gates pass:

```text
content hash matches
row count matches
promotion_state == verified_promoted
retention_policy == temporary_delete_after_verified_promotion
```

Until then, delete remains blocked.

## Desktop status panel

The desktop panel shows:

```text
writer targets
implemented codecs
manifest-only codecs
sample table manifests
retention gate status
next phase
```

Files:

```text
tauri-app/src/storage-writers.sample.json
tauri-app/src/storage_writers.js
```

## Files

```text
configs/storage_v2_writers.v311_v320.json
data/storage_v2/v311_v320/storage_v2_writers.sample.json
docs/storage_v2_writers_v311_v320.md
rust-core/src/storage_v2_writers_v311.rs
tauri-app/src/storage-writers.sample.json
tauri-app/src/storage_writers.js
python_lab/storage_v2_writers_smoke.py
.github/workflows/v311_v320_storage_v2_writers.yml
```

## Acceptance

v311-v320 is accepted when:

```text
JSONL.Zstd writer is defined in Rust
JSON.Zstd writer is defined in Rust
JSONL.Gzip compatibility is preserved
provider cache manifest writer is defined
Bronze manifest verification is defined
Silver/Gold manifest writers are defined
row counts and content hashes are required
retention gates are defined
storage writer status panel is added
Python smoke and CI workflow are added
no live calls, credentials, or recommendation output are introduced
```
