# v471-v480 Desktop Beta Release Readiness

This phase checks that OmniBet Lab is moving toward a real downloadable Windows/Linux desktop beta without confusing the beta GUI with a validated prediction engine.

## Included versions

```text
v471 beta vs model quality policy
v472 desktop release workflow readiness check
v473 Windows release asset readiness
v474 Linux release asset readiness
v475 Tauri metadata alignment check
v476 portable package content check
v477 release notes safety check
v478 downloadable beta user path check
v479 CI release readiness smoke
v480 release readiness docs
```

## Current release workflow

The release workflow is:

```text
.github/workflows/desktop_release.yml
```

It is manually triggered by `workflow_dispatch` and accepts:

```text
release_tag
release_name
prerelease
draft
```

It builds on:

```text
windows-latest
ubuntu-latest
```

The intended user path is:

```text
Windows: download zip, extract, run OmniBet-Lab.exe
Linux: download tar.gz, extract, run ./omnibet-lab
```

## Metadata alignment

The Tauri and package versions must remain aligned:

```text
tauri-app/src-tauri/tauri.conf.json
tauri-app/package.json
```

Current expectation:

```text
productName = OmniBet Lab
identifier = local.omnibet.lab
bundle.active = true
bundle.targets = all
```

## Safety policy

This phase depends on:

```text
docs/beta_vs_model_quality_policy.md
```

The release beta can improve packaging, GUI flow, local file previews, report viewing, and offline sample usability. It must not unlock model trust claims.

```text
GUI beta can move fast.
Prediction/training engine must move slow.
```

The release must keep:

```text
ready_for_training = false
recommendation_output_present = false
credential_values_present = false
live_provider_calls_allowed = false
```

## Release notes safety language

Release notes must make clear:

```text
PAPER_ONLY
not betting recommendations
not staking advice
not proof of edge
```

## Next

The next phase should move from readiness checks to actual release artifact hardening:

```text
v481-v490 GitHub release artifacts / downloadable beta flow
```

That phase should verify generated release archives, manifest hashes, included GUI samples, and user-facing README instructions.
