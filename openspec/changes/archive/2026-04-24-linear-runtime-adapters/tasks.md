# Tasks: Linear Runtime Adapters (Phase 2)

## Phase 0: Prerequisite decisions (blocking)

- [x] 0.1 Finalize normalized error enum (`PRECHECK_FAILED`, `AUTH`, `NETWORK`, `VALIDATION`, `REMOTE`, `UNKNOWN`) in `.ai/workflows/sdd-linear/contracts/runtime-outcome.schema.json` and reflect same names in design notes.
- [x] 0.2 Decide live close policy (fully disabled vs test-project-only) and encode rule in `.ai/workflows/sdd-linear/config.json` (`runtime.live.smokePolicy`).
- [x] 0.3 Decide explicit live confirmation UX (flag/prompt text) and align `.opencode/commands/sdd-linear/sdd-*.md` plus `.atl/skills/sdd-linear-flow/SKILL.md`.
- [x] 0.4 Decide reconciliation-required operator UX for partial success output in `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` and command docs.

## Phase 1: Contracts and runtime foundation

- [x] 1.1 Add `runtime` config defaults (`mode: stub`, `allowedModes`, live preflight toggles, smoke policy) in `.ai/workflows/sdd-linear/config.json`.
- [x] 1.2 Create `.ai/workflows/sdd-linear/contracts/runtime-outcome.schema.json` for `requestedAction`, `observedResult`, and normalized `error`.
- [x] 1.3 Create `.ai/workflows/sdd-linear/contracts/runtime-preflight.schema.json` for pass/fail checks and `allowSideEffects`.
- [x] 1.4 Update `.ai/workflows/sdd-linear/contracts/change-metadata.schema.json` to add backward-safe `runtime` + `adapterOutcomes` structures.
- [x] 1.5 Create `.ai/workflows/sdd-linear/runtime/ports.py` and `.ai/workflows/sdd-linear/runtime/adapters/stub.py` with deterministic no-side-effect responses.

## Phase 2: Core adapter orchestration (apply-friendly batches)

- [x] 2.1 In `.ai/workflows/sdd-linear/bin/sdd_linear_core.py`, parse/validate runtime mode (default `stub`, reject unknown modes fast).
- [x] 2.2 Batch A: wire adapter dispatcher for `status` sync path; persist normalized outcome metadata for success/failure.
- [x] 2.3 Batch B: wire adapter dispatcher for `log_issue` path; persist per-system outcomes and keep bounded retry policy unchanged.
- [x] 2.4 Batch C: wire adapter dispatcher for `archive` path; record gate result + adapter outcomes while preserving evidence policy ownership in core.
- [x] 2.5 Add legacy metadata compatibility: initialize missing `adapterOutcomes` safely when loading Phase 1 files.

## Phase 3: Live mode, preflight, and wrapper integration

- [x] 3.1 Create `.ai/workflows/sdd-linear/runtime/preflight.py` for credentials/connectivity/target-scope checks and smoke-safe evaluation.
- [x] 3.2 Create `.ai/workflows/sdd-linear/runtime/adapters/live.py` mapping vendor responses/errors into normalized outcome schema.
- [x] 3.3 Integrate preflight into core live path (fail fast before side effects, persist blocked outcomes and diagnostics).
- [x] 3.4 Update `.opencode/commands/sdd-linear/sdd-new.md`, `sdd-status.md`, `sdd-log-issue.md`, and `sdd-archive.md` to pass runtime mode and surface core JSON unchanged.
- [x] 3.5 Update `.atl/skills/sdd-linear-flow/SKILL.md` with optional live confirmation guidance only (no workflow policy logic).

## Phase 4: Verification and sync

- [x] 4.1 Extend `tests/test_sdd_linear_batch4.py` for scenarios: stub default, invalid mode rejection, live preflight fail, archive close blocked by smoke policy, and partial-success persistence.
- [x] 4.2 Add `tests/test_sdd_linear_runtime_adapters.py` for unit coverage (ports, normalization, preflight evaluator) and integration checks (dispatcher stub/live paths).
- [x] 4.3 Update `scripts/bootstrap-sdd-linear.sh` managed-file list to include new runtime modules and runtime contract schemas.
