# Verification Report

**Change**: linear-runtime-adapters
**Version**: N/A
**Mode**: Standard

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 22 |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

---

## Build & Tests Execution

**Build / type-check**: ➖ Not run

- Constraint: repository instructions explicitly say **never run build steps**.

**Tests**: ✅ 31 passed / ❌ 0 failed / ⚠️ 0 skipped

Command:

```bash
python3 -m unittest discover -s tests
```

Output:

```text
...............................
----------------------------------------------------------------------
Ran 31 tests in 0.538s

OK
```

**Coverage**: ➖ Not available (not configured)

---

## Spec Compliance Matrix (behavioral)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| OpenCode wrapper MUST select runtime mode and stay thin | Default wrapper behavior | `tests/test_sdd_linear_batch4.py > AdapterAndBootstrapContractTests.test_command_wrappers_document_runtime_passthrough_and_live_confirmation` ; `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_create_change_persists_linear_linked_metadata` | ✅ COMPLIANT |
| OpenCode wrapper MUST select runtime mode and stay thin | Live mode invocation | `tests/test_sdd_linear_batch4.py > AdapterAndBootstrapContractTests.test_command_wrappers_document_runtime_passthrough_and_live_confirmation` ; `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_status_live_preflight_failure_persists_blocked_outcome_and_diagnostics` | ✅ COMPLIANT |
| State sync MUST execute via runtime adapters and persist outcomes | Sync success through adapter | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_status_updates_report_local_and_mapped_state` | ✅ COMPLIANT |
| State sync MUST execute via runtime adapters and persist outcomes | Sync adapter failure | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_status_records_normalized_failure_outcome_when_adapter_errors` | ✅ COMPLIANT |
| Derived-issue fallback MUST preserve canonical record under partial success | Engram success, Linear failure | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_log_issue_records_partial_success_outcomes_when_linear_retry_is_still_needed` | ✅ COMPLIANT |
| Derived-issue fallback MUST preserve canonical record under partial success | Linear success, Engram follow-up failure | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_log_issue_marks_reconciliation_required_when_linear_succeeds_but_engram_follow_up_fails` | ✅ COMPLIANT |
| Archive flow MUST gate live side effects using adapter outcomes | Live close blocked | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_archive_live_mode_blocks_close_via_smoke_policy_but_keeps_comment_path` | ✅ COMPLIANT |
| Archive flow MUST gate live side effects using adapter outcomes | Live archive comment allowed | `tests/test_sdd_linear_batch4.py > WorkflowCoreBatch4Tests.test_archive_live_mode_blocks_close_via_smoke_policy_but_keeps_comment_path` | ✅ COMPLIANT |

**Compliance summary**: 8/8 scenarios compliant

---

## Correctness (static — structural evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Wrapper resolves runtime mode, stays thin | ✅ Implemented | Wrapper definitions in `.opencode/commands/sdd-linear/*.md` document `runtimeMode`, explicit live confirmation UX, and “return core JSON unchanged”. |
| State sync via adapter + normalized outcomes persisted | ✅ Implemented | `WorkflowCore.status()` dispatches via `runtime_adapter(mode).sync_status(...)` and persists `adapterOutcomes.statusSync[]` in metadata. |
| Partial success preserves Engram canonical record + bounded retry/manual fallback (including reconciliation-required) | ✅ Implemented | Core records per-system outcomes; distinguishes retryable Linear failures vs the reconciliation-required “Linear exists, Engram linkage update failed” branch without duplicating Linear creation. |
| Archive live side-effects gated by evidence + smoke policy + adapter outcomes | ✅ Implemented | Live close is blocked when smoke policy fails; blocked outcome is persisted alongside allowed adapter outcomes. |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Core calls explicit ports (ports + adapters) | ✅ Yes | `runtime/ports.py`, `runtime/adapters/{stub,live}.py`, core `runtime_adapter()` dispatcher. |
| `stub` default + explicit `live` | ✅ Yes | `config.json` runtime defaults to `stub`; core rejects unknown modes. |
| Normalize outcomes (`requestedAction`, `observedResult`, `error`) | ✅ Yes | Schemas + `make_outcome()`; persisted under `adapterOutcomes`. |
| Stage 1 live close gated/disabled | ✅ Yes | `runtime.live.smokePolicy.allowClose=false` + core smoke-policy close blocking in live mode. |

---

## Issues Found

### CRITICAL (must fix before archive)

- None

### WARNING (should fix)

- Running `python3 -m unittest` at repo root executes **0 tests**; test discovery requires `python3 -m unittest discover -s tests`. Consider documenting a single canonical verify test command.

### SUGGESTION (nice to have)

- Add `openspec/config.yaml` (or equivalent) with `rules.verify.test_command` so verification doesn’t rely on executor inference.
- Close/resolve remaining “Decision Notes (TODO)” entries in delta specs now that wrappers and reconciliation UX are implemented.

---

## Verdict

**PASS WITH WARNINGS** — Phase 2 scope is satisfied and all spec scenarios have passing behavioral coverage; minor repo ergonomics/docs remain.
