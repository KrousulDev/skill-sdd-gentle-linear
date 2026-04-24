# Design: Linear Runtime Adapters

## Technical Approach

Phase 2 keeps the Phase 1 neutral core (`sdd_linear_core.py`) as policy owner, and adds explicit runtime ports selected by `runtime.mode` (`stub` default, `live` opt-in). Core decisions (state mapping, retry budget, archive gate, manual fallback) stay unchanged; adapters execute side effects and return normalized outcomes persisted in local metadata.

## Architecture Decisions

| Decision | Option | Tradeoff | Selected |
|---|---|---|---|
| Adapter wiring | Wrapper calls vendors directly | Faster demo, policy duplication/lock-in | No |
|  | Core calls explicit ports | Slight setup cost, preserves neutral-core contract | **Yes** |
| Runtime mode | `live` by default | Real coverage, unsafe local baseline | No |
|  | `stub` default + explicit `live` | Safe baseline, explicit operator intent | **Yes** |
| Outcome model | Store raw vendor payloads | Rich detail, unstable contracts | No |
|  | Normalize (`requestedAction`, `observedResult`, `error`) | Slight mapping work, durable retries/reconciliation | **Yes** |
| Live rollout | Enable close immediately | Fast parity, highest operational risk | No |
|  | Stage 1 live = comment/update; close gated by smoke policy | Safer rollout, phased capability | **Yes** |

## Data Flow

`/sdd-log-issue` (same pattern for status/archive):

Wrapper (`--runtime-mode`) → Core preflight (live only) → Port dispatcher
→ Engram adapter + Linear adapter
→ normalized outcomes aggregator
→ metadata persistence (`changes/{change}.json`)
→ wrapper surfaces core JSON unchanged

Partial success path:

Engram success + Linear failure → `outcomes[]` records both systems → core retry/manual fallback uses canonical local metadata.

## File Changes

| File | Action | Description |
|---|---|---|
| `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` | Modify | Add runtime-mode parsing, preflight invocation, adapter-port orchestration, normalized outcome persistence. |
| `.ai/workflows/sdd-linear/config.json` | Modify | Add `runtime` section (`mode`, adapter settings, smoke policy, live action scope). |
| `.ai/workflows/sdd-linear/contracts/change-metadata.schema.json` | Modify | Add `runtime`/`adapterOutcomes` structures to persist normalized results. |
| `.ai/workflows/sdd-linear/contracts/runtime-outcome.schema.json` | Create | Contract for requested/observed/error outcome records. |
| `.ai/workflows/sdd-linear/contracts/runtime-preflight.schema.json` | Create | Contract for preflight diagnostics and block reasons. |
| `.ai/workflows/sdd-linear/runtime/ports.py` | Create | Neutral adapter interfaces for Linear and Engram operations. |
| `.ai/workflows/sdd-linear/runtime/adapters/stub.py` | Create | Deterministic no-side-effect adapters used by default and tests. |
| `.ai/workflows/sdd-linear/runtime/adapters/live.py` | Create | Live adapters wrapping Linear/Engram execution and error normalization. |
| `.ai/workflows/sdd-linear/runtime/preflight.py` | Create | Credential/connectivity/target-scope checks and smoke-safe policy gating. |
| `.opencode/commands/sdd-linear/sdd-*.md` | Modify | Wrapper contract for mode selection and passthrough of preflight/outcomes. |
| `.atl/skills/sdd-linear-flow/SKILL.md` | Modify | Optional UX guidance for live confirmations; no workflow logic ownership. |
| `tests/test_sdd_linear_batch4.py` | Modify | Extend current contract tests for stub default, live preflight fail, partial success persistence. |
| `tests/test_sdd_linear_runtime_adapters.py` | Create | Focused runtime adapter unit/integration tests (ports, preflight, normalization). |
| `scripts/bootstrap-sdd-linear.sh` | Modify | Include new runtime and contract files in managed sync list. |

## Interfaces / Contracts

```json
// config.json (new section)
"runtime": {
  "mode": "stub",
  "allowedModes": ["stub", "live"],
  "live": {
    "requireExplicitOptIn": true,
    "preflight": {"credentials": true, "connectivity": true, "targetScope": true},
    "smokePolicy": {"allowClose": false, "allowedLinearProjects": ["TEST"]}
  }
}
```

```json
// normalized outcome (runtime-outcome.schema.json)
{
  "system": "linear|engram",
  "requestedAction": {"type": "create_issue|update_state|comment|close|save_observation", "targetId": "string|null"},
  "observedResult": {"status": "success|failed|blocked|skipped", "remoteId": "string|null", "timestamp": "ISO-8601"},
  "error": {"code": "PRECHECK_FAILED|AUTH|NETWORK|VALIDATION|REMOTE|UNKNOWN|null", "message": "string|null", "retryable": "boolean|null"}
}
```

```json
// live preflight result (runtime-preflight.schema.json)
{"status":"pass|fail","checks":[{"name":"credentials|connectivity|targetScope","status":"pass|fail","detail":"string"}],"allowSideEffects":true}
```

Metadata evolution (backward-safe): if `adapterOutcomes` missing, core treats as legacy Phase 1 file and initializes defaults.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Port contracts, normalization map, preflight evaluator | Pure Python tests with stubbed adapter responses. |
| Integration | Core + adapter dispatcher for stub/live paths | Temp workspace + fixture metadata; assert persisted outcomes and unchanged policy decisions. |
| E2E/Smoke | Live opt-in guarded flows | Non-destructive designated test targets only; required only when `runtime.mode=live`. |

## Migration / Rollout

No destructive migration required. Rollout is additive:
1) ship contracts + stub adapters, 2) wire core to ports with `stub` default, 3) enable live preflight path, 4) enable live comment/update, 5) gate close behind explicit smoke policy.

## Resolved Phase 0 Decisions

- Final normalized error enum is `PRECHECK_FAILED`, `AUTH`, `NETWORK`, `VALIDATION`, `REMOTE`, `UNKNOWN`.
- Initial live close policy is **fully disabled** via `runtime.live.smokePolicy.allowClose = false`; no Linear projects are allow-listed in this first runtime batch.

## Open Questions

- [ ] Confirm wrapper UX for explicit live confirmation prompt text.

## Implementation Sequencing Guidance

1. Add schemas and `config.runtime` first (no behavior change).
2. Introduce ports + stub adapters; wire core dispatcher with `stub` default.
3. Persist normalized `adapterOutcomes` for status/log-issue/archive.
4. Add live adapters + preflight; fail fast on preflight errors before side effects.
5. Update wrappers/helper docs to pass mode and surface diagnostics unchanged.
6. Expand tests (legacy Phase 1 compatibility + new runtime cases).
7. Update bootstrap managed file list last.
