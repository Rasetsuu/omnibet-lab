# v511-v520 Prediction Result Cards

This phase fixes the simple Matches GUI so pressing prediction buttons gives visible, friendly results.

## Problem

The app already ran a local paper prediction, but the result was easy to miss because it appeared as a raw JSON wall below the fold.

That made the GUI feel like nothing happened.

## New behavior

```text
Select match
Press Predict selected
See a clean Prediction result card
Raw JSON is hidden inside a details section
```

For all loaded local fixtures:

```text
Press Predict all paper
See one clean paper result card per match
```

## Normal user path

The normal GUI should stay:

```text
Matches
Select
Predict selected
Predict all paper
Result/status
```

Training, materialization, imports, and evaluation remain internal or advanced-only concepts.

## Safety

The cards keep paper-only language. They are not recommendations and not staking advice.

## Next

Next practical phase:

```text
v521-v530 background model/data status
```

That should add a small status indicator such as:

```text
Model: preview
Data: local World Cup pack
Training: internal/locked/not visible as a button
```
