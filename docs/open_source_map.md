# Open-source map / what to borrow

This is a research map for OmniBet Lab. The repo does not vendor third-party source code; it borrows architectural ideas and lists upstreams to inspect further.

## Highest-value football source

### penaltyblog
Useful ideas to port or interop with:
- Poisson, bivariate Poisson, Dixon-Coles and Bayesian match modelling.
- Elo/Massey/Colley/Pi team ratings.
- implied-probability / overround removal.
- market probability helpers for totals, Asian handicap, match odds.
- StatsBomb / Opta / Understat data workflows.

OmniBet v0 borrows the *shape* of this architecture: `data -> ratings -> model -> markets -> odds/value`.

## Strong cross-sport architecture references

### NBA_Betting
Useful ideas:
- SQLite-style unified storage with game data, betting market data and feature data.
- point-in-time feature engineering to prevent leakage.
- market lines as both benchmark and possible feature.
- bankroll / Kelly module.
- web dashboard for predictions and betting performance.

OmniBet v0 borrows the *database-first, time-aware feature pipeline* idea.

## Smaller useful football repos found

- ZenFish13/dixoncoles: useful for comparing classic Dixon-Coles implementation details.
- maxantcliff/football_poisson_2 and FootballMatchPredictionPoisson repos: useful as simple baselines only.
- danielsaed/futbol_corners_forecast: useful because corners should be modelled separately from goals rather than forced from xG.

## What not to blindly copy

- Claims of high betting accuracy without walk-forward validation.
- In-sample ROI screenshots.
- Models that use match-final statistics to predict the same match.
- Any dataset without stable `match_id`, ISO `date`, home/away team mapping and source audit.

## OmniBet target architecture

1. Unified match registry.
2. Point-in-time features.
3. Sport-specific models but shared betting/value layer.
4. Multiple model families per market.
5. Calibration layer.
6. Walk-forward backtest.
7. Odds ingestion + overround removal.
8. Bankroll simulation.
9. GUI + CLI.
