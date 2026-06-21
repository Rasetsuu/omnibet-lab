# v259 Source Generate Refresh

v259 adds a desktop flow for generating and refreshing the local source report.

## Desktop flow

```text
click Generate source report
run generate_source_terminal_report
write .omnibet-local/reports/local_v256_source_terminal_report.json
reload source view
```

## Buttons

```text
generate-source-terminal-report
generate-source-terminal-report-topbar
```

Both buttons call the same frontend helper:

```text
generateAndRenderSourceTerminal
```

## Safety

The flow remains local-only, paper-only, and read-only. It writes a local report for inspection and then refreshes the source view.

## Next batch

v260 should make the source view more useful for beta work by adding row sample details and filters for the generated report.
