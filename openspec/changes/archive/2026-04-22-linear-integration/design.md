# Design: Linear Integration (Fase 1)

## Technical Approach

Build a **neutral core** in `./.ai/workflows/sdd-linear/` that owns workflow rules, contracts, templates, and runtime metadata. Add one **OpenCode/gentle-ai adapter** that translates commands to core operations but does not contain business rules. Linear MCP and Engram are accessed through explicit ports so Fase 1 remains portable and configuration-driven.

## Architecture Decisions

### Decision: Core-first portable architecture

| Option | Tradeoff | Decision |
|---|---|---|
| Adapter-first in `.opencode/` | Fast demo, high lock-in | Rejected |
| Neutral core + thin adapter | Slightly more setup, high portability | **Chosen** |

### Decision: Runtime metadata as file-per-change

| Option | Tradeoff | Decision |
|---|---|---|
| In-memory/session only | Simple, not durable | Rejected |
| `./.ai/workflows/sdd-linear/changes/{change}.json` | Durable, auditable, merge-visible | **Chosen** |

### Decision: Engram-first derived issue handling

| Option | Tradeoff | Decision |
|---|---|---|
| Linear-first then record memory | Possible data loss if Linear fails | Rejected |
| Save to Engram first, then Linear retries (max 3) | Slightly longer flow, canonical trace | **Chosen** |

### Decision: Declarative SDD→Linear mapping

| Option | Tradeoff | Decision |
|---|---|---|
| Hardcoded statuses | Fragile across workspaces | Rejected |
| `state-map.json` many→few mapping | Needs config discipline | **Chosen** |

### Decision: Fase 1 default Linear states are intentionally minimal

| Option | Tradeoff | Decision |
|---|---|---|
| Mirror every SDD state in Linear | Rich visibility, heavy rollout dependency | Rejected |
| Map to `Backlog`, `In Progress`, `Done` only | Lower fidelity, portable across most workspaces | **Chosen** |

Rationale: Fase 1 explicitly tolerates many SDD states collapsing into fewer Linear states. Using a minimal default avoids assuming custom workspace setup for QA/business-validation columns while still preserving the richer local SDD state in metadata.

### Decision: V1 metadata stays in one file per change with nested evidence/derived records

| Option | Tradeoff | Decision |
|---|---|---|
| Split files per concern | Finer writes, more coordination complexity | Rejected |
| Single `{change}.json` with nested `archive` + `derivedIssues` | Slightly larger payload, simpler portability/audit | **Chosen** |

Rationale: the repository is document-first and Fase 1 is focused on portability. A single runtime file per change keeps inspection, sync, and bootstrap behavior simple while still allowing nested contracts for archive evidence and derived issue retries.

### Decision: `/sdd-archive` uses local evidence gates only in Fase 1

| Option | Tradeoff | Decision |
|---|---|---|
| Revalidate remote Linear state before close | Stronger safety, more MCP coupling and failure modes | Rejected for Fase 1 |
| Trust local evidence gate and configured close policy | Simpler and portable, weaker remote verification | **Chosen** |

Rationale: Fase 1 already requires explicit PR, merge, QA, and business validation evidence. Adding remote revalidation now would enlarge the dependency surface before the neutral core is stable.

### Decision: OpenCode ships commands-first, helper-skill optional

| Option | Tradeoff | Decision |
|---|---|---|
| Commands + mandatory helper skill | More guidance, higher install coupling | Rejected |
| Commands-only core with optional `sdd-linear-flow` helper | Less assisted UX, neutral core stays operable | **Chosen** |

Rationale: the adapter must remain functional without project-local skill installation. The helper skill can improve operator experience later, but command wrappers stay the non-blocking baseline.

## Data Flow

`/sdd-new`

User Input → Adapter → Core Validator (`linearIssueId` required)
→ Core Metadata Store (`changes/{change}.json`) → Status response

`/sdd-log-issue`

Adapter / operator flow → canonical Engram save outside the core
→ Core DerivedIssue Service records retry outcomes (attempt 1..3)
→ success: metadata.derivedIssues[].linearIssueId
→ fail: metadata.derivedIssues[].manualFallback

`/sdd-archive`

Adapter → Core Gate Evaluator (PR URL, mergeConfirmed, qaNotes, businessValidation)
→ fail: block + missing fields
→ pass: render template + close-eligibility flags → archive metadata

Fase 1 boundary note: the neutral core intentionally returns render/eligibility artifacts instead of executing Linear comment or close side effects directly. Adapter/operator layers own external delivery.

## File Changes

| File | Action | Description |
|---|---|---|
| `.ai/workflows/sdd-linear/config.json` | Create | Core config (ports, policies, retries, close behavior). |
| `.ai/workflows/sdd-linear/state-map.json` | Create | Declarative mapping from SDD states to Linear states. |
| `.ai/workflows/sdd-linear/templates/archive-comment.md` | Create | Structured archive comment template. |
| `.ai/workflows/sdd-linear/templates/manual-derived-issue.md` | Create | Manual fallback payload/prompt template. |
| `.ai/workflows/sdd-linear/contracts/change-metadata.schema.json` | Create | Change metadata contract for runtime files. |
| `.ai/workflows/sdd-linear/contracts/derived-issue.schema.json` | Create | Derived issue and retry/fallback contract. |
| `.ai/workflows/sdd-linear/contracts/archive-evidence.schema.json` | Create | Minimum archive evidence gate contract. |
| `.ai/workflows/sdd-linear/bin/sdd_linear_core.py` | Create | Neutral-core CLI implementing metadata creation, state mapping, derived issue persistence, and archive gate rendering. |
| `.ai/workflows/sdd-linear/changes/.gitkeep` | Create | Runtime path anchor for per-change metadata files. |
| `.opencode/commands/sdd-linear/*.md` | Create | OpenCode command wrappers calling core contracts. |
| `.atl/skills/sdd-linear-flow/SKILL.md` | Create | Optional helper skill; non-blocking if missing. |
| `scripts/bootstrap-sdd-linear.sh` | Create | Idempotent installer/regenerator for managed assets. |

## Interfaces / Contracts

```json
{
  "changeId": "linear-integration",
  "linear": {"issueId": "LIN-123", "featureId": "PROJ-1"},
  "workflow": {"sddState": "review", "mappedLinearState": "In Progress"},
  "archive": {
    "evidence": {"prUrl": "", "mergeConfirmed": false, "qaNotes": "", "businessValidation": ""},
    "gate": {"status": "blocked|pass", "missing": []}
  },
  "derivedIssues": [
    {
      "engramObservationId": 0,
      "retry": {"attempted": 0, "max": 3},
      "linearIssueId": null,
      "manualFallback": {"required": false, "payload": "", "prompt": ""}
    }
  ],
  "unresolved": []
}
```

Unresolved-item contract (to avoid blocking implementation):

```json
{"id":"U-001","topic":"default-linear-states","status":"provisional","decisionNeededBy":"sdd-apply","fallback":"use state-map.json only; no hardcoded default"}
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Schema validation, state mapping, gate evaluation, retry policy | Table-driven tests over JSON fixtures. |
| Integration | Adapter↔core contract, Engram-first ordering, Linear retry/fallback behavior | Stub ports for Engram and Linear MCP. |
| E2E | `/sdd-new`, `/sdd-status`, `/sdd-log-issue`, `/sdd-archive` happy/edge paths | Scripted command flows over temp project workspace. |

## Migration / Rollout

No data migration required. Rollout is additive and idempotent via bootstrap.

## Open Questions

- [ ] Canonical default Linear status names shipped in first `state-map.json`.
- [ ] Whether `/sdd-archive` must revalidate remote Linear state before close in Fase 1.
- [ ] Final adapter packaging split (`.opencode` commands only vs commands + helper skill guidance).

Resolved by apply foundation/core work:

- [x] Canonical default Linear states ship as `Backlog`, `In Progress`, `Done` in `state-map.json`.
- [x] `/sdd-archive` remote revalidation stays disabled in Fase 1; local evidence gate is canonical.
- [x] Adapter packaging is commands-first with optional helper skill support.

## Fase 1 Layout and Sequencing Guidance

Proposed layout:

```text
.ai/workflows/sdd-linear/
  config.json
  state-map.json
  contracts/
  templates/
  changes/
```

Implementation sequence for next phases:
1. Create neutral folders/contracts/templates + sample config/state map.
2. Implement metadata read/write + validators.
3. Implement state mapping + `/sdd-status` reporting.
4. Implement derived issue flow (Engram first, Linear retry, manual fallback).
5. Implement archive evidence gate + comment rendering + close policy.
6. Add OpenCode adapter wrappers and optional `sdd-linear-flow` helper behavior.
7. Finalize bootstrap script once managed paths are stable.
