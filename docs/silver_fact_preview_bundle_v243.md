# v243 Silver Fact Preview Bundle

v243 creates the first tiny offline silver fact preview bundle.

It is still not a training dataset.

## Preconditions

The bundle can only build when:

```text
silver_ready input is true
review queue is clean
```

If the review queue is dirty, the bundle builder refuses to create rows.

## Inputs

```text
v242 patched silver promotion preview
v242 patched review queue report
```

## Expected offline result

```text
market fact rows: 7
identity link rows: 15
total rows: 22
review rows at build time: 0
preview only: true
training dataset promotion allowed: false
```

## Row kinds

```text
market_mapping_fact_preview
identity_link_fact_preview
```

## Safety

```text
preview only
training promotion forbidden
dirty review queue refused
```

## Why this matters

This is the first place where the pipeline produces clean canonical silver-style rows after:

```text
provider parsing
bronze cache
market registry
identity mapping
review queue
sample market review patch
```

It proves the gate works end-to-end while still preventing accidental training-data promotion.

## Next step

v244 should materialize this preview bundle into a verifiable local JSONL.GZ artifact, similar to the bronze cache, but with silver-preview schema and strict no-training flags.
