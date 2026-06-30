# v831 Counts Report

This phase adds a tiny count report after the v801 row builder.

## Commands

```bash
python python_lab/v831_counts.py
```

## Outputs

```text
reports/v831_counts.json
reports/ci_v831_counts.json
```

## Expected current status

```text
row_count: 3
minimum_rows: 200
ready: false
status: needs_more_rows
```

This is correct until larger local row packs are added.
