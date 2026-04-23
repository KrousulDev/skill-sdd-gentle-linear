# Tasks: Linear Integration (Fase 1)

## Batch 0 — Prerequisite Decisions (blocks implementation)

- [x] 0.1 Define default Fase 1 Linear statuses in `./.ai/workflows/sdd-linear/state-map.json` and document rationale in `openspec/changes/linear-integration/design.md`.
- [x] 0.2 Finalize v1 metadata granularity (change, derived issue, archive evidence) in `./.ai/workflows/sdd-linear/contracts/change-metadata.schema.json`.
- [x] 0.3 Decide `/sdd-archive` remote revalidation policy; encode choice in `./.ai/workflows/sdd-linear/config.json` and archive command docs.
- [x] 0.4 Finalize manual fallback payload fields/order in `./.ai/workflows/sdd-linear/templates/manual-derived-issue.md` and `contracts/derived-issue.schema.json`.
- [x] 0.5 Confirm OpenCode packaging mode (commands-only vs commands+helper) and record non-blocking helper behavior in `.opencode/commands/sdd-linear/*.md`.

## Batch 1 — Neutral Core Foundation (apply batch A)

- [x] 1.1 Create core structure: `./.ai/workflows/sdd-linear/{contracts,templates,changes}/` and `changes/.gitkeep`.
- [x] 1.2 Create `./.ai/workflows/sdd-linear/config.json` with retry policy (3), archive gate policy, and close behavior flags.
- [x] 1.3 Create `./.ai/workflows/sdd-linear/state-map.json` implementing many-SDD-to-few-Linear mapping (no hardcoded fallback).
- [x] 1.4 Author schemas: `contracts/change-metadata.schema.json`, `contracts/derived-issue.schema.json`, `contracts/archive-evidence.schema.json`.
- [x] 1.5 Author templates: `templates/archive-comment.md` and `templates/manual-derived-issue.md` with required evidence/payload placeholders.

## Batch 2 — Core Workflow Behaviors (apply batch B)

- [x] 2.1 Implement `/sdd-new` flow in adapter/core wiring to require `linearIssueId`, accept optional `linearFeatureId`, and create per-change metadata under `changes/{change}.json`.
- [x] 2.2 Implement `/sdd-status` mapping read from `state-map.json`, returning local SDD state + mapped Linear state, and config error on unmapped states.
- [x] 2.3 Implement `/sdd-log-issue` Engram-first flow: save derived issue first, then Linear retries (max 3), then manual fallback metadata.
- [x] 2.4 Implement `/sdd-archive` evidence gate requiring `prUrl`, `mergeConfirmed`, `qaNotes`, `businessValidation`, persisting gate results in metadata.
- [x] 2.5 Render archive completion comments from `templates/archive-comment.md`; block close/comment actions when gate fails.

## Batch 3 — OpenCode Adapter + Bootstrap (apply batch C)

- [x] 3.1 Create `.opencode/commands/sdd-linear/` command wrappers for `/sdd-new`, `/sdd-status`, `/sdd-log-issue`, `/sdd-archive` consuming neutral-core assets.
- [x] 3.2 Add optional helper skill `.atl/skills/sdd-linear-flow/SKILL.md` that enhances UX but keeps core workflow fully operable without it.
- [x] 3.3 Create `scripts/bootstrap-sdd-linear.sh` to install/regenerate managed paths idempotently and print created/updated/skipped summary.
- [x] 3.4 Ensure bootstrap includes next-step guidance for credentials/sync and never stores secrets in repo files.

## Batch 4 — Verification for Spec Scenarios (apply batch D)

- [x] 4.1 Add contract fixtures/tests for schemas and state mapping happy/edge cases from `linear-change-linking` and `linear-state-sync` specs.
- [x] 4.2 Add integration tests/stubs validating Engram-first ordering, 3-attempt retry, and manual fallback from `derived-issue-fallback` spec.
- [x] 4.3 Add archive gate tests for pass + missing field block from `archive-evidence-gates` spec, including “no close action on failure”.
- [x] 4.4 Add adapter tests for helper-present and helper-absent behavior from `opencode-sdd-linear-adapter` spec.
- [x] 4.5 Add bootstrap idempotency test/verification for first-run install vs re-run reconciliation from `sdd-linear-bootstrap` spec.
