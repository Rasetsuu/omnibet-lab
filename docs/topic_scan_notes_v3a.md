# GitHub Topic Scan Notes

The `nba-prediction` and `football-prediction` topic scans did not replace the main plan, but they confirm several useful patterns.

## Useful extra patterns found

- NBA projects commonly use SQLite for stats/odds/history.
- XGBoost and neural nets are common baselines for moneyline and totals.
- EV and Kelly output are standard in stronger betting tools.
- Football projects often use rolling last-N game features such as goals, shots, corners, possession, and fouls.
- Calibration matters because raw classifier probabilities are often overconfident.
- Public bookmaker/Vegas lines are an extremely hard benchmark and can be used as a market prior.

## Project decision

Keep penaltyblog as the football modelling reference and NBA_Betting as the architecture reference. Use topic repos as idea confirmation, not as code to copy blindly.
