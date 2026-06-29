# v491-v500 Beta Open-and-Walk GUI

This phase makes the desktop beta feel less like a developer dashboard and more like an app a user can open and understand.

## Included versions

```text
v491 beta home contract
v492 default start page
v493 guided demo card
v494 historical import card
v495 materialization card
v496 World Cup paper lab placeholder
v497 training lock explainer
v498 open-walk release notes
v499 CI open-walk GUI smoke
v500 open-walk GUI docs
```

## New default page

The app now defaults to:

```text
Start Here
beta-home
```

Instead of opening directly into the debug-style Dashboard, the user sees a simple start page with four obvious paths:

```text
Start with demo
Import historical files
View materialization
World Cup paper lab
```

## Why

The existing GUI works, but it is too counterintuitive for a beta tester. It has many buttons and internal reports. This phase keeps those advanced/debug pages available while creating a calmer first screen.

## World Cup paper lab placeholder

This page does not connect to live providers yet. It only documents the next safe path:

```text
completed matches can become historical training/evaluation rows
upcoming matches can be paper-predicted before kickoff
settled results are attached only after match completion
```

## Safety lock

The beta home page must keep:

```text
ready_for_training = false
trust_status = sample_only
live_provider_calls_allowed = false
recommendation_output_present = false
credential_values_present = false
```

## Next

After this phase, the next practical phase should be:

```text
v501-v510 World Cup local fixture pack and paper lab
```

That should add local fixture data first, not live scraping. Once it works locally, the GUI can expose a simple one-button paper prediction flow.
