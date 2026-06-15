# Event and Player Model Roadmap

The long-term model must understand *when* goals/events happen and *who* causes them.

## New tables needed

```text
events
shots
goals
lineups
substitutions
player_match_stats
player_snapshots
team_snapshots
referee_snapshots
injuries_suspensions
transfers
```

## Goal timing targets

- goal in first 15 minutes
- goal before minute X
- first goal time
- team to score first
- goal in both halves
- highest scoring half
- late goal probability

## Player targets

- anytime goalscorer
- first goalscorer
- player shots
- player shots on target
- player assists
- player cards
- expected minutes
- lineup strength

## Player score idea

```text
player_score =
  attacking_score
  + defensive_score
  + possession_score
  + physical_score
  + position_fit_score
  + league_strength_adjustment
  + recent_form
  - discipline_risk
  - availability_risk
```

## Rotation / reserve detection

For favorites vs weaker teams, lineup strength matters more than badge strength. The model must learn whether a team is likely using its best XI or rotating.
