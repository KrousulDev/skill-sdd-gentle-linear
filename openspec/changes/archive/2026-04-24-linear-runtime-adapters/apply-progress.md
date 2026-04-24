# Apply Progress: linear-runtime-adapters

## Change
`linear-runtime-adapters`

## Mode
Standard

## Completed Tasks
- [x] 0.1 Finalize normalized runtime error enum and reflect it in design notes.
- [x] 0.2 Choose fully-disabled live close policy for the first runtime batch and encode it in config.
- [x] 0.3 Decide explicit live confirmation UX across wrappers and helper skill.
- [x] 0.4 Decide reconciliation-required operator UX for partial success output.
- [x] 1.1 Add runtime config defaults (`stub` default, allowed modes, live preflight toggles, smoke policy).
- [x] 1.2 Create runtime outcome schema.
- [x] 1.3 Create runtime preflight schema.
- [x] 1.4 Extend change metadata schema with backward-safe `runtime` and `adapterOutcomes`.
- [x] 1.5 Add runtime ports and deterministic stub adapter foundation.
- [x] 2.1 Parse and validate runtime mode in core, defaulting to `stub` and rejecting unknown modes.
- [x] 2.2 Wire status sync through the adapter dispatcher and persist normalized success/failure outcomes.
- [x] 2.3 Wire adapter dispatcher for `log_issue` and persist per-system outcomes without changing retry/manual fallback policy.
- [x] 2.4 Wire adapter dispatcher for `archive`, persisting gate result plus normalized archive outcomes while keeping evidence policy in core.
- [x] 2.5 Backfill missing runtime metadata safely for legacy Phase 1 metadata files.
- [x] 3.1 Create the live preflight evaluator for credentials/connectivity/target-scope checks.
- [x] 3.2 Add the pluggable live runtime adapter module and factory with normalized outcome/error mapping.
- [x] 3.3 Integrate live preflight into status/log-issue/archive flows, failing fast before side effects and persisting blocked outcomes/diagnostics.
- [x] 3.4 Update wrapper commands to pass runtime mode through and surface core JSON unchanged.
- [x] 3.5 Update helper skill guidance for optional live confirmation.
- [x] 4.1 Extend batch tests for live preflight failure and smoke-policy close blocking.
- [x] 4.2 Add focused runtime adapter unit/integration coverage for preflight and live dispatch paths.
- [x] 4.3 Update bootstrap managed-file sync for runtime modules and contracts.

## Corrective Batch
- Added explicit reconciliation handling for the approved spec scenario where Linear creation succeeds but the Engram follow-up linkage update fails.
- Persisted reconciliation-required metadata (`status: reconciliation-required`, `reconciliationRequired: true`) alongside normalized adapter outcomes showing Engram failure and Linear success.
- Added explicit regression coverage for the missing scenario while preserving existing Engram-first retry/manual-fallback behavior.

## Files Changed
| File | Action | What Was Done |
|---|---|---|
| `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` | Modified | Added Engram follow-up reconciliation handling, operator guidance, and CLI flags for explicit linkage failure reporting. |
| `.ai/workflows/sdd-linear/runtime/adapters/stub.py` | Modified | Normalized the Engram follow-up failure path without duplicating Linear issue creation. |
| `.ai/workflows/sdd-linear/contracts/derived-issue.schema.json` | Modified | Added reconciliation-required metadata support for derived issues. |
| `tests/test_sdd_linear_batch4.py` | Modified | Added explicit regression coverage for Linear-success/Engram-follow-up-failure behavior and updated schema assertions. |
| `openspec/changes/linear-runtime-adapters/apply-progress.md` | Created | Recorded cumulative apply progress plus the corrective batch details. |

## Deviations from Design
None — the fix preserves Engram-first policy ownership in the neutral core and only adds the missing reconciliation branch required by spec.

## Issues Found
- `openspec/config.yaml` is still absent, so execution remains in Standard mode by repository fallback and orchestrator context.

## Remaining Tasks
- None.

## Status
22/22 tasks complete. Corrective batch applied; ready for verify.
