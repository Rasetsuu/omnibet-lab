# v231 Release + World Cup Live Capture Foundation

v231 starts two practical tracks after desktop build stabilization:

1. GitHub Releases become the user-facing desktop download path.
2. World Cup 2026 becomes the first serious live-capture/training campaign.

## Release path

The workflow is:

```text
.github/workflows/desktop_release.yml
```

It is manual-only via `workflow_dispatch` and creates GitHub Release assets:

```text
OmniBet-Lab-Windows-<tag>.zip
OmniBet-Lab-Linux-<tag>.tar.gz
```

The release should be draft + prerelease by default until the package is manually opened on both Windows and Linux.

Release package entrypoints:

```text
Windows: OmniBet-Lab.exe
Linux:   ./omnibet-lab
```

The release remains PAPER_ONLY. It is not a betting recommendation product and not a signed production installer.

## World Cup 2026 capture policy

The World Cup campaign is a live capture and leak-safe training campaign, not a shortcut to live betting.

Before match:

```text
fixture discovery
odds snapshots
market discovery
lineups when available
paper prediction snapshot
```

During match:

```text
live state snapshots
event snapshots
odds movement snapshots
```

After match:

```text
final-state settlement
market settlement
CLV report
paper ledger update
training dataset promotion
```

Training is allowed only after a match is final, and only for future predictions. Random train/test split is not allowed; walk-forward evaluation is required.

## Planned sources

Initial source contracts are disabled by default and have no live calls in CI:

```text
The Odds API      odds snapshots + market discovery
API-Football      fixtures + live state + lineups + events
Sportmonks        secondary fixture/live/event source
Betfair Exchange  exchange reference + historical backtest
```

Credential names are stored, credential values are never stored or displayed.

## Raw-data retention

Raw provider payloads are temporary audit/replay material.

Default policy:

```text
raw payloads: keep locally for 30 days, then delete or compress after promotion
canonical facts: keep
feature rows: keep
labels: keep
manifests/hashes: keep
model configs/evaluations: keep
```

This keeps reproducibility without hoarding raw provider payloads longer than needed.

## Acceptance

- GitHub release workflow exists and is manual-only.
- Release config declares Windows/Linux assets and entrypoints.
- World Cup source contract includes provider roles and safety policy.
- Live providers are disabled by default.
- CI performs no external provider calls.
- Training policy requires final matches, future-only prediction use, walk-forward splits, and no-vig baseline comparison.
