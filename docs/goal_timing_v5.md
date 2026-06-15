# Goal Timing v5

Goal timing is a separate target family from final score.

## Targets

- first goal minute
- first goal team
- goal 0-15
- goal 16-30
- goal 31-45
- goal 46-60
- goal 61-75
- goal 76-90
- first-half goals
- second-half goals

## Why it matters

Bet-builder markets often include:

- goal before minute X
- goal after minute X
- first team to score
- goal in both halves
- highest scoring half
- player first goalscorer

These require event timestamps, not just final scores.

## Command

```bash
cd python_lab
python goal_timing_lab.py --db ../build/omnibet.sqlite
```

If no event data exists, the script reports insufficient data honestly.
