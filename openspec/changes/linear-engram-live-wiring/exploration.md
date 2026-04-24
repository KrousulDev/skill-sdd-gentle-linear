## Exploration: linear-engram-live-wiring

### Current State
Phase 2 already ships the neutral-core/runtime split: `sdd_linear_core.py` owns workflow policy, `runtime/ports.py` defines normalized outcome contracts, `runtime/adapters/stub.py` is the safe default, and `runtime/adapters/live.py` can execute real side effects only when handlers are injected. The gap is now operational, not architectural: `build_live_runtime_adapter()` is called without real handlers by default, so `live` mode is opt-in and preflight-aware, but not wired to the user's actual Linear or Engram accounts.

The scope jump for this change is therefore **live-ready → live-wired**:
- keep workflow policy in the neutral core
- add real handler wiring for Linear and Engram operations
- keep `stub` as the default safe mode
- define smoke-safe validation against real accounts without normalizing unsafe “full production” behavior

### Affected Areas
- `docs/PHASE-2-BUSINESS-CASES.md` — states the exact business gap: runtime/live exists, real account wiring does not.
- `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` — already owns mode selection, preflight gating, normalized outcomes, reconciliation, and archive safety boundaries.
- `.ai/workflows/sdd-linear/runtime/adapters/live.py` — current live adapter is only a dispatcher/normalizer; it lacks default real handlers.
- `.ai/workflows/sdd-linear/runtime/preflight.py` — current preflight validates env presence and smoke scope, but not vendor-specific auth/account identity.
- `.ai/workflows/sdd-linear/config.json` — current live config has safe defaults (`stub`, explicit opt-in, `allowClose=false`) and is the right place for bounded live policy, not secrets.
- `.opencode/commands/sdd-linear/*.md` and `.atl/skills/sdd-linear-flow/SKILL.md` — wrappers already enforce `ALLOW_SDD_LINEAR_LIVE`; they must stay thin and MUST NOT own vendor logic.
- `tests/test_sdd_linear_runtime_adapters.py` / `tests/test_sdd_linear_batch4.py` — current tests prove normalization and guard rails, but not real-account smoke wiring.

### Approaches
1. **Default live wiring via dedicated real-handler factory** — keep `LiveRuntimeAdapter` generic, but introduce a project-local wiring module that builds real Linear/Engram handlers from env/config and injects them into the live adapter.
   - Pros: preserves neutral-core contract, keeps vendor code isolated, supports stub/live parity, allows smoke-safe substitution in tests.
   - Cons: requires explicit handler contracts per operation and vendor-specific preflight checks.
   - Effort: Medium.

2. **Inline vendor calls inside `live.py` or core** — replace handler injection with direct Linear/Engram API logic in the existing runtime/core files.
   - Pros: faster first live demo.
   - Cons: collapses the adapter boundary, mixes policy with integration code, makes future replacement/testing harder, and increases credential leakage risk.
   - Effort: Low initially / High long-term cost.

### Recommendation
Choose **Default live wiring via dedicated real-handler factory**.

Recommended responsibility split:

- **Neutral core (`sdd_linear_core.py`) MUST continue owning**
  - runtime mode selection and safe defaulting
  - metadata persistence and normalized outcome recording
  - SDD→Linear state mapping
  - Engram-first derived-issue policy, retry budget, manual fallback, and reconciliation-required logic
  - archive evidence gate and smoke-policy close blocking

- **Real Linear handlers MUST own**
  - resolving/authenticating the real Linear client/session
  - `sync_status`: map requested state into the actual remote update call
  - `log_issue`: create the derived Linear issue and return remote identifiers
  - `archive`: perform comment and optional close attempts, respecting already-computed `comment_allowed` / `close_allowed`
  - translating remote failures into normalized adapter errors without leaking raw vendor payloads into policy

- **Real Engram handlers MUST own**
  - resolving/authenticating the real Engram client/session
  - creating or updating the canonical observation/event record used by `/sdd-log-issue`
  - follow-up linkage/update after Linear success so the existing `reconciliation-required` path can be driven by real outcomes
  - returning stable observation identifiers and normalized failure signals

- **Wrappers/helper UX MUST own only**
  - collecting operator inputs
  - enforcing `ALLOW_SDD_LINEAR_LIVE`
  - passing `runtimeMode` and surfacing core JSON unchanged

Credentials, secrets, and preflight boundaries:

- `LINEAR_API_KEY` and `ENGRAM_API_KEY` are the current minimum env gates already modeled by preflight.
- Proposal/spec should add **identity validation**, not just presence checks: confirm the reachable workspace/account and report it in preflight diagnostics.
- Secrets MUST remain env-driven or runtime-injected; they SHOULD NOT be stored in `config.json`, OpenSpec artifacts, or change metadata.
- Preflight SHOULD split into:
  - credential presence
  - credential validity / identity probe
  - connectivity
  - target-scope safety
  - operation safety (comment/update allowed first; close remains separately gated)

Safe validation strategy:

- Start with a **sandbox/smoke** plan, not broad live rollout.
- Smoke path SHOULD validate in this order:
  1. preflight-only identity check (no side effects)
  2. live `status` on a designated smoke issue/project
  3. live `log-issue` against a designated disposable/sandbox parent
  4. live `archive` comment-only on a smoke target
  5. live close only after an explicit later policy decision
- Smoke evidence MUST capture remote IDs in local metadata and produce an operator-readable audit trail.
- Real-account validation SHOULD require designated sandbox targets; it MUST NOT run by default against arbitrary production work items.

### Risks
- **Credential presence is not enough**: current preflight can pass with env vars set but still target the wrong workspace/account unless identity checks are added.
- **Split-brain remains the top operational risk**: live Linear success + Engram linkage failure is already modeled, but real handlers must preserve it exactly or operators will duplicate issues.
- **Archive close is still the riskiest action**: enabling real close too early can mutate real work irreversibly; comment/update should ship first.
- **Vendor leakage risk**: if handler payloads or exceptions bleed into core policy/contracts, the neutral architecture regresses.
- **Wrapper overreach risk**: adding real vendor calls to wrapper docs/skills would duplicate orchestration and weaken portability.
- **Missing OpenSpec config**: this repo currently has no `openspec/config.yaml`, so proposal/spec must keep relying on existing project conventions rather than assumed per-phase config rules.

### Ready for Proposal
Yes — ready if the proposal frames this as **real live wiring with strict safety boundaries**, not as “turn live on everywhere.” The proposal should define a dedicated real-handler factory/module, operation-level handler responsibilities, stronger preflight/identity checks, sandbox smoke validation, and explicit non-goals around default-on live mode and unrestricted close behavior.
