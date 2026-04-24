## Exploration: linear-runtime-adapters

### Current State
Phase 1 already proved the neutral-core shape: `.ai/workflows/sdd-linear/` owns workflow rules, contracts, templates, local metadata, and render-only outputs, while OpenCode wrappers stay thin and the optional helper skill stays non-blocking. The current Python core writes local JSON metadata and computes intended Linear/Engram outcomes, but it does not execute real Linear MCP actions or real Engram persistence during runtime; those boundaries are still caller-owned/documented rather than implemented adapters.

### Affected Areas
- `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` — current neutral CLI; Phase 2 must stop short of hardcoding vendor side effects here while introducing adapter ports.
- `.ai/workflows/sdd-linear/config.json` — must grow explicit runtime mode/adapter config without turning environment details into business rules.
- `.ai/workflows/sdd-linear/contracts/*.json` — likely needs adapter outcome contracts for sync attempts, persistence results, and smoke-test-safe assertions.
- `.opencode/commands/sdd-linear/*.md` — wrappers currently describe caller-owned boundaries; Phase 2 must define when wrappers invoke stub vs live adapters.
- `.atl/skills/sdd-linear-flow/SKILL.md` — guidance may need runtime-mode/operator rules, but it still must not own workflow logic.
- `tests/test_sdd_linear_batch4.py` — current tests validate Phase 1 contracts only; Phase 2 needs stub/live adapter coverage and smoke-path assertions.
- `README.md`, `docs/RUNBOOK.md`, `docs/REAL_TEST_CASES_TEST_REPO.md` — already declare Phase 2 themes: real Linear/Engram adapters, stub/live modes, stronger persistence, and end-to-end execution.

### Approaches
1. **Core-owned ports + pluggable runtime adapters** — keep workflow decisions in the neutral core, but introduce explicit Linear and Engram adapter interfaces selected by config/mode.
   - Pros: preserves Phase 1 architecture, enables stub/live parity, keeps OpenCode thin, makes smoke tests safe.
   - Cons: requires a small runtime abstraction layer before real side effects.
   - Effort: Medium.

2. **Wrapper-driven live integrations** — keep the core mostly unchanged and let `.opencode` wrappers call Linear/Engram tools directly before/after core commands.
   - Pros: faster first live demo.
   - Cons: duplicates orchestration logic, weakens portability, makes non-OpenCode adapters harder, and blurs test boundaries.
   - Effort: Low initially / High later.

3. **Core executes live vendors directly** — embed Engram and Linear tool assumptions inside `sdd_linear_core.py`.
   - Pros: simplest single-process implementation.
   - Cons: breaks the neutral-core promise, couples Python runtime to agent/tooling details, and makes local/offline smoke tests brittle.
   - Effort: Medium initially / High architectural cost.

### Recommendation
Choose **Core-owned ports + pluggable runtime adapters**. The practical Phase 2 jump should be: keep Phase 1’s neutral domain contracts intact, add runtime adapter contracts for `LinearRuntimeAdapter` and `EngramRuntimeAdapter`, and let the OpenCode layer only select/drive `stub` or `live` mode. Neutral core responsibilities should remain: change metadata lifecycle, state mapping, retry policy, archive gate evaluation, payload/comment rendering, and persistence of adapter outcomes. Live adapters should own: actual Linear lookup/create/update/comment/close side effects, actual Engram save/update calls, tool-specific error normalization, and connectivity-aware smoke execution.

### Phase 2 Boundary Clarification
- **Remain in neutral core**
  - workflow state machine and many-to-few state mapping
  - required evidence rules and archive gate decisions
  - derived-issue retry budget and manual fallback generation
  - canonical metadata schema for requested action + observed adapter result
  - runtime-mode selection contract and adapter response normalization
- **Move into live adapters**
  - real Linear MCP/project issue operations
  - real Engram save/update operations
  - translation from tool failures into normalized adapter error objects
  - environment/credential dependency checks
  - optional smoke-test probes against live services
- **Stay in OpenCode wrappers / helper UX only**
  - collecting missing operator inputs
  - selecting stub/live mode from config or explicit command intent
  - surfacing adapter results without rewriting rules

### Safest Sequencing
1. Define adapter ports and normalized result contracts first, without changing Phase 1 behavior.
2. Add `runtime.mode` support (`stub` default, `live` opt-in) in config and metadata so existing tests remain green by default.
3. Implement stub adapters that simulate Linear/Engram side effects but write deterministic outcomes for tests.
4. Add integration tests that execute wrapper/core flows through stub adapters end to end.
5. Add live adapters behind explicit opt-in and credential preflight checks.
6. Add smoke tests that run only in live mode, assert non-destructive success paths first, and never become mandatory for baseline local validation.

### Architecture and Risk Decisions Before Proposal/Spec
- Phase 2 MUST treat `stub` as the safe default and `live` as explicit opt-in; otherwise bootstrap portability and local testing become fragile.
- Adapter contracts SHOULD persist both `requestedAction` and `observedResult` into change metadata; otherwise troubleshooting live failures will be opaque.
- Linear and Engram failures MUST be normalized into portable status/error shapes in the core contract; raw tool output should not leak into business rules.
- Live archive/comment/close behavior SHOULD be introduced in layers: comment/update first, close last, because close is the most operationally risky side effect.
- Smoke tests MUST target bounded, reversible operations or explicitly designated test issues/projects; otherwise “validation” can mutate real work.
- The helper skill must remain optional even in live mode; credentials/runtime readiness cannot depend on `.atl/skills/` existing.

### Risks
- Phase 2 can accidentally collapse the architecture if wrappers or the Python core start embedding vendor-specific tool calls.
- Live mode can corrupt real Linear state if smoke tests are not scoped to disposable/test entities.
- Engram/Linear partial success creates split-brain risk unless adapter outcomes are durably recorded in local metadata.
- Making live mode the default would break current portability and contradict Phase 1’s contract-first validation model.

### Ready for Proposal
Yes — ready if the proposal frames Phase 2 as **runtime adapter introduction**, not a rewrite: explicit ports, stub-first sequencing, live opt-in, metadata-backed outcome recording, and smoke tests gated behind safe environment checks.
