# GitHub topic scan notes

The topic scan was intentionally light: the goal was not to clone every toy project, but to avoid missing obvious architecture or modelling ideas before the v2 work.

## NBA topic findings

Useful extra reference: `kyleskom/NBA-Machine-Learning-Sports-Betting`.

Ideas worth borrowing:

- SQLite-backed data collection for stats and odds.
- Feature construction from stats + odds + rest days.
- Separate moneyline and totals models.
- XGBoost / neural net baselines.
- Expected value and Kelly sizing in the prediction output.
- Manual odds input fallback when automated odds are unavailable.
- Flask-style web output for simple browsing.

This does **not** replace the `NBA_Betting/NBA_Betting` architecture reference. It reinforces it.

## Football topic findings

Useful extra reference: `mhaythornthwaite/Football_Prediction_Project`.

Ideas worth borrowing:

- Rolling previous-N-game form windows.
- Difference features: goal difference, shot difference, corners difference, possession difference, pass accuracy difference, fouls difference.
- Calibration checks: a model can have acceptable raw accuracy but unreliable probability estimates.
- Draw prediction is hard and should be evaluated separately.

This does **not** replace penaltyblog. Penaltyblog remains the strongest reference for serious football statistical modelling.

## Decision

The v2 direction remains:

1. Build a real SQLite feature store.
2. Add a proper Dixon-Coles optimizer/backtest lab.
3. Keep cross-sport abstractions clean.
4. Only port stable math to Rust/C++ after proof-of-concept validation.
