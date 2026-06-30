# v651-v680 Rust File Adapters

This phase adds Rust parsers for the local adapter sample file shapes.

## Added module

```text
rust-core/src/adapter_file_parsers_v651.rs
```

## Parsers

```text
parse_football_data_csv_v651
parse_openfootball_json_v651
parse_statsbomb_events_json_v651
build_pack_from_sample_contents_v651
```

## Scope

The parsers target the local sample files added in v591-v620.

No network calls are made.

The output pack remains preview-only.

## Next

```text
file-backed CLI runner
larger local historical row packs
batch preview runtime
```
