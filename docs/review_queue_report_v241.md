# v241 Review Queue Report

v241 turns silver-promotion blockers into explicit human-review rows.

The current sample is blocked by one unresolved market:

```text
special_combo_unknown
```

## Input

```text
v240 silver promotion preview
```

## Output

```text
ReviewQueueReport
  market_review_rows
  identity_review_rows
  total_review_rows
  auto_approval_allowed: false
```

## Expected offline result

```text
total review rows: 1
market review rows: 1
identity review rows: 0
review required: true
silver ready after review: false
```

## Required fields for market review

A market review row must require:

```text
canonical_market_id
market_family
settlement_rule
selection_scope
line_required
player_required
lineup_required
correlation_group
```

This prevents a vague mapping from unblocking silver facts.

## Required fields for identity review

Identity review rows must require:

```text
canonical_id
entity_kind
display_name
provider_entity_id_or_name
```

## Safety

```text
auto approval is forbidden
review rows block silver readiness
promotion before review is forbidden
training promotion remains forbidden
```

## Next step

v242 can add an approved-alias patch path for the sample unknown market, but only by adding a full canonical market definition, settlement rule, selection scope, and correlation group. The app should then show the review queue going from blocked to clean in a controlled test.
