# v258 Source Report Generation

v258 adds a local generator for the desktop source view.

## Workflow

```text
generate_source_terminal_report
```

The workflow writes:

```text
.omnibet-local/reports/local_v256_source_terminal_report.json
```

The v257 desktop loader checks this path before falling back to the bundled sample.

## Generator

```text
python_lab/source_terminal_generate.py
```

It reads the offline v254 fixture samples and emits the source-terminal report shape used by the desktop page.

Expected generated status:

```text
adapter count: 2
adapter OK count: 2
normalized total rows: 5
odds snapshot candidates: 3
fixture result candidates: 1
event context candidates: 1
```

## Safety

```text
paper only: true
local only: true
network calls: false
credential storage: false
read-only desktop surface: true
```

## Next batch

v259 should add a desktop button/flow that runs `generate_source_terminal_report` from the source-terminal page and refreshes the panel after generation.
