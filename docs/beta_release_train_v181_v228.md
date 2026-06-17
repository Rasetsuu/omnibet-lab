# v181-v228 Beta Release Train

This release train groups the next six beta-prep phases into one CI-gated product pass.

## Phase 1: v181-v188 QA and stabilization

Validates the local happy path: load samples, import local data, import cached fixtures, select a fixture, preview the result, and export a snapshot.

## Phase 2: v189-v196 Build readiness

Keeps the manual Windows/Linux desktop build workflow as the packaging path and verifies artifact naming/checksum contracts.

## Phase 3: v197-v204 Local persistence contract

Documents the local app data layout under `.omnibet-local` for imports, forecasts, workflow state, exports, cache, and logs.

## Phase 4: v205-v212 Evaluation path

Defines the next evaluation contract: chronological split, per-competition and global metrics, calibration bins, and report-only gates until real history files are validated.

## Phase 5: v213-v220 Setup contracts

Keeps setup manual and opt-in. Configuration is metadata-only and must not store secret values in repository files.

## Phase 6: v221-v228 Beta release prep

Defines the beta tag template, manual OS test requirements, release notes checklist, artifact checklist, and post-release verification.

## Boundaries

- Paper-only research preview.
- Local-first desktop workflow.
- Manual opt-in for any external setup.
- No automatic external calls in CI.
- No secret values in repository files.
- Not a final product release.
