# Proposal: Linear Runtime Adapters

## Intent

Phase 2 adds real runtime behavior for Linear and Engram without breaking the neutral-core contract proven in Phase 1. The goal is to move side effects behind explicit ports so the workflow stays portable, testable, and safe by default.

## Scope

### In Scope
- Add neutral runtime ports for Linear and Engram plus normalized result/error contracts.
- Introduce `runtime.mode` with `stub` default and explicit `live` opt-in.
- Implement stub adapters, live adapters, metadata outcome recording, and smoke-safe preflight rules.
- Update OpenCode wrappers to select modes and surface adapter results without owning workflow rules.

### Out of Scope
- Rewriting core workflow rules or moving business logic into wrappers/skills.
- Making live mode the default.
- Unbounded destructive live validation; close/archive side effects stay layered and cautious.
- New product features unrelated to runtime integration.

## Capabilities

### New Capabilities
- `runtime-adapters`: defines Linear/Engram ports, stub/live adapter behavior, normalized outcomes, and preflight/smoke contracts.

### Modified Capabilities
- `opencode-sdd-linear-adapter`: wrappers must select runtime mode and remain thin.
- `linear-state-sync`: sync must run through adapter ports and persist observed results.
- `archive-evidence-gates`: archive flow must record live adapter outcomes and gate risky close behavior.
- `derived-issue-fallback`: real Engram/Linear runtime persistence must preserve retry and manual fallback guarantees.

## Approach

Keep state mapping, retry policy, archive gates, rendering, and metadata ownership in the neutral core. Add adapter ports consumed by the core; `stub` adapters produce deterministic safe outputs, while `live` adapters perform real Linear/Engram calls behind credential checks and normalized error handling.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` | Modified | Port orchestration and metadata result recording |
| `.ai/workflows/sdd-linear/config.json` | Modified | Runtime mode and adapter config |
| `.ai/workflows/sdd-linear/contracts/` | Modified | Adapter result/error contracts |
| `.opencode/commands/sdd-linear/` | Modified | Mode selection and result surfacing |
| `tests/test_sdd_linear_batch4.py` | Modified | Stub/live-path and smoke-safe coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Vendor logic leaks into core/wrappers | Med | Enforce ports and spec boundaries |
| Live mode mutates real work | Med | Stub default, opt-in live, scoped smoke rules |
| Partial success causes split-brain | High | Persist requested + observed adapter outcomes locally |

## Open Decisions

- Exact adapter contract fields for `requestedAction`, `observedResult`, and normalized errors.
- Which live actions ship first in spec/design: comment/update only vs limited close support.
- Preflight contract shape for credentials, connectivity, and designated smoke-test targets.
- Whether metadata/schema deltas belong in existing change files or a dedicated runtime outcome document.

## Rollback Plan

Disable `live` mode, keep `stub` as the active runtime, and revert adapter-specific wiring while preserving Phase 1 metadata/contracts.

## Dependencies

- Existing Phase 1 neutral-core assets and specs
- Credential/preflight strategy for live Linear and Engram execution

## Success Criteria

- [ ] Specs can define runtime adapters without weakening the neutral core.
- [ ] Default local flow remains safe and deterministic in `stub` mode.
- [ ] Live mode is explicit, preflight-checked, and records normalized outcomes.
- [ ] Wrapper/core behavior stays contract-driven and smoke-test-safe.
