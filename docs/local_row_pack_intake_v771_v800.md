# v771-v800 Local Row Pack Intake

This phase creates the local intake path for larger completed row packs.

## Why

The v1 roadmap says the next real step is larger historical row packs.

This PR does not pretend the model is trained. It only adds the local scanner/reporting layer needed before larger packs are added.

## Intake folder

```text
data/local_historical/
```

## Supported first file shapes

```text
*.csv   football-data shaped match rows
*.json  openfootball shaped match rows or event-shaped rows
```

## Scanner

```bash
python python_lab/local_row_pack_intake_scan.py
```

Outputs:

```text
reports/ci_v771_v800_local_row_pack_intake.json
reports/local_row_pack_scan_v771_v800.json
```

## Gate status

Current repo sample rows are enough for a scanner smoke, not enough for v1 baseline work.

```text
minimum rows for v1 baseline: 200
current expected status: needs_more_rows_for_v1_baseline
```

## Next

Add or point to real completed local row packs, then build the feature builder v1 only after row counts and timestamp checks are healthy.
