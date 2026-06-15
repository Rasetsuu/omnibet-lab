# v17 Paper Betting Ledger and CLV Skeleton

v17 adds the first paper-only ledger and closing-line-value skeleton.

## New files

```text
data/sample_closing_odds_spain_cape_verde.csv
python_lab/paper_betting_ledger.py
```

## What it does

The script reads the Rust value report and a sample closing-odds CSV. It creates:

- `paper_bets`
- `clv_snapshots`

It only writes paper-bet rows for positive-edge selections and requires all rows to remain `PAPER ONLY` under the low-trust gate.

## Command

```bash
cd python_lab

python paper_betting_ledger.py \
  --db ../build/omnibet.sqlite \
  --value-report ../reports/ci_rust_value_report.json \
  --closing-odds ../data/sample_closing_odds_spain_cape_verde.csv \
  --out ../reports/ci_paper_ledger.json \
  --fixture-id Spain-vs-Cape-Verde
```

## CI contract

CI now requires:

- `paper_bets_written > 0`
- `clv_rows_written > 0`
- `all_paper_only = true`

## Honesty

This is a paper ledger only. It is not a real-money staking system and does not imply a betting edge.
