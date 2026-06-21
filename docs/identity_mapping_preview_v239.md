# v239 Identity Mapping Preview

v239 adds the first safe fixture/team/player identity preview before provider rows can become silver football facts.

This is separate from market mapping. A market can be known while its fixture, team, or player identity is still unsafe.

## Inputs

```text
The Odds API-style event markets sample
API-Football-style live state sample
v239 identity alias contract
```

## Offline sample result

Expected identity references:

```text
fixture refs: 2
team refs: 4
player refs: 9
total refs: 15
resolved refs: 15
review refs: 0
blocked promotions: 0
```

The references cover:

```text
The Odds API fixture id: toa_event_france_senegal_demo
API-Football fixture id: 123456
France / Senegal team identities across both providers
API-Football lineup/event players
The Odds API name-only Kylian Mbappe player-prop participant
```

## Safety rules

```text
preview only
unknown identities cannot be auto-promoted
provider alias required
fixture identity required before match facts
team identity required before team facts
player identity required before player facts
review required for unmapped identities
```

## Rust module

The implementation lives in:

```text
rust-core/src/identity_mapping_v239.rs
```

It is exported through a short wrapper:

```text
rust-core/src/idmap_v239.rs
```

The wrapper avoids connector naming friction while still compiling the implementation through the Rust core crate.

## Why this matters

Before World Cup live capture can become real training data, the app must know that these are the same real-world entities:

```text
the_odds_api: France
api_football team id 10: France
canonical: team_france_men
```

And similarly:

```text
the_odds_api name-only Kylian Mbappe prop participant
api_football player id 1001: Kylian Mbappe
canonical: player_kylian_mbappe
```

Without this layer, player props, lineups, scorer markets, team stats, and events could be mixed incorrectly.

## Next step

v240 should combine the market preview and identity preview into a silver promotion report: safe rows move to a preview-only silver fact bundle, while unresolved market/entity rows remain blocked in review.
