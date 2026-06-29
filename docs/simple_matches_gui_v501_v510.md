# v501-v510 Simple Matches GUI

This phase changes the normal desktop beta from a developer dashboard into a match-first app screen.

## Included versions

```text
v501 simple matches contract
v502 normal mode matches page
v503 hide debug navigation in normal mode
v504 hide topbar debug buttons in normal mode
v505 World Cup local fixture pack
v506 predict selected paper button
v507 predict all paper placeholder
v508 background training status hidden from normal GUI
v509 CI simple matches GUI smoke
v510 simple matches GUI docs
```

## Normal mode

Normal mode should show only:

```text
Matches
Select match
Predict selected
Predict all paper
Result/status
```

It should not show the internal report wall by default.

## Hidden by default

The following remain available in code, but should not be the first user experience:

```text
training controls
materialization controls
import controls
calibration reports
baseline reports
storage/debug pages
```

These should later move behind an Advanced mode.

## Local World Cup fixture pack

The first local pack is:

```text
tauri-app/src/world-cup-fixtures.local.json
```

It contains the June 29, 2026 Round-of-32 local fixtures used for beta testing:

```text
Brazil vs Japan
Germany vs Paraguay
Netherlands vs Morocco
```

This is local data for UI testing and paper predictions.

## Training direction

Training should not be a normal GUI button. The intended direction is:

```text
background checks local completed-match data
background safe training/evaluation when data changes
GUI shows only model/data status
```

Unsettled/current matches are not training rows. They can only be paper-prediction rows until settled.

## Next

The next phase should wire the World Cup paper lab into a real one-screen flow:

```text
v511-v520 batch paper predictions and result tracking
```
