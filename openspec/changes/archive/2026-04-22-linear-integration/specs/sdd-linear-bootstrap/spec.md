# sdd-linear-bootstrap Specification

## Purpose
Define safe, repeatable bootstrap behavior for neutral workflow assets and initial adapter setup.

## Requirements

### Requirement: Bootstrap MUST be idempotent and scope-bounded
Bootstrap MUST install or regenerate managed assets for `./.ai/workflows/sdd-linear/` and initial OpenCode adapter wiring, MUST be safe to re-run, and MUST report managed paths and actions.

#### Scenario: Happy path first install
- GIVEN a project without SDD-Linear assets
- WHEN bootstrap runs
- THEN required neutral-core files and adapter entrypoints are installed
- AND output includes next-step guidance for credentials/sync

#### Scenario: Edge case re-run on existing setup
- GIVEN managed assets already exist
- WHEN bootstrap runs again
- THEN managed assets are reconciled idempotently
- AND an action summary states created/updated/skipped paths

## Decision Notes (TODO)
- Decide managed-sync strategy: full template copy vs managed-path selective sync.
- Decide initial canonical Linear status names for Fase 1 mapping defaults.
- Finalize v1 metadata schema granularity for change/evidence files.
