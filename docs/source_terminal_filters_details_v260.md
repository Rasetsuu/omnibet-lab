# v260 Source Terminal Filters and Row Details

v260 makes the Source Terminal useful for beta work before OmniBet moves into upcoming/live fixture contracts.

The v259 flow could generate and refresh a local source report. v260 keeps that flow and adds local inspection controls:

```text
provider filter
row-type filter
readiness filter
blocker filter
adapter health details
normalized row sample details
next-action hints
```

## Scope

This milestone is still read-only and paper-only. It does not enable live provider calls, model fitting, bronze writes, or downstream promotion.

## Desktop UX

The Source Terminal page now renders two additional local inspection panels:

```text
source-terminal-filters
source-terminal-row-details
```

The filters are local UI-only controls over rows already present in the report. The detail panel shows the selected sample payload and the next review action.

## Report shape

v260 accepts legacy count-only reports, but the useful path is a report containing:

```text
adapter_health[]
normalized_preview_rows[]
```

Each normalized preview row should expose:

```text
row_id
provider
row_type
readiness
blocker_reason
next_action
sample
```

Missing row details fall back to count-only placeholder rows so old generated reports remain inspectable.

## Safety

```text
paper_only: true
read_only: true
live_provider_calls: false
secrets_displayed: false
promotion_actions: false
```

Rows remain quarantined/read-only until later source, identity, market, silver, and gold promotion gates explicitly allow movement.

## Acceptance

v260 is accepted when:

```text
v259 generate-refresh buttons still work
source report can be filtered by provider/type/readiness/blocker
row sample details can be inspected locally
adapter health details are visible
no live provider call or secret display is introduced
README, contract, sample, and smoke are updated
```
