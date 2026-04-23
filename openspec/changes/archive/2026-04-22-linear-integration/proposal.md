# Proposal: Linear Integration

## Intent

Define a portable Fase 1 backbone that links SDD changes to Linear without coupling the workflow to a single agent. The goal is traceable issue-driven execution, mandatory derived-issue capture, and archive gating with minimum evidence.

## Scope

### In Scope
- Neutral workflow assets under `./.ai/workflows/sdd-linear/`.
- Declarative config, templates, and `state-map.json` for many SDD states → fewer Linear states.
- Per-change runtime metadata in `./.ai/workflows/sdd-linear/changes/`.
- Derived-issue contract: Engram save first, up to 3 Linear retries, then manual fallback payload.
- Archive gate contract for PR URL, merge confirmed, QA notes, and business validation.
- One OpenCode/gentle-ai adapter plus existence contract for `sdd-linear-flow`.
- Bootstrap contract for installing/regenerating the neutral core and initial adapter.

### Out of Scope
- Automated feature/project close.
- Adapters beyond OpenCode.
- Rich TUI/new shell UX.
- Deep Linear workspace provisioning beyond initial mapping support.

## Capabilities

### New Capabilities
- `linear-change-linking`: require Linear issue linkage and optional feature/project linkage for SDD changes.
- `linear-state-sync`: load declarative state mapping and synchronize bounded workflow states.
- `derived-issue-fallback`: persist derived findings to Engram and produce Linear/manual fallback handling.
- `archive-evidence-gates`: validate minimum archive evidence before close/comment actions.
- `opencode-sdd-linear-adapter`: let OpenCode consume the neutral core without owning business rules.
- `sdd-linear-bootstrap`: define safe, idempotent installation/regeneration behavior.

### Modified Capabilities
None.

## Approach

Adopt a **core-first neutral architecture**: rules, metadata schema, templates, and integration contracts live in `./.ai/workflows/sdd-linear/`; agent-specific behavior stays in adapters. Linear and Engram sit behind explicit boundaries so Fase 1 proves the workflow without locking the domain into `.atl/` or `.opencode/`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `PRD-linear-integration.md` | Modified | Source constraints and rollout assumptions |
| `openspec/changes/linear-integration/proposal.md` | New | Fase 1 scope contract |
| `./.ai/workflows/sdd-linear/` | New | Neutral core root |
| `.atl/`, `.opencode/` | New/Modified | OpenCode adapter surface |
| `scripts/bootstrap-sdd-linear.sh` | New | Bootstrap contract target |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fase 1 scope creep | Med | Freeze to issue-level backbone only |
| Hardcoded Linear statuses | High | Keep mapping external/config-driven |
| Weak archive evidence schema | Med | Spec explicit evidence fields next |

## Rollback Plan

Revert introduced workflow artifacts and adapter wiring, preserve PRD/OpenSpec documents, and continue with manual SDD + Engram tracking. No repo secrets or irreversible data migrations are part of Fase 1.

## Dependencies

- `PRD-linear-integration.md`
- Engram persistence for derived issues and summaries
- Linear MCP access and workspace status mapping

## Success Criteria

- [ ] Fase 1 scope is bounded to neutral core + one OpenCode adapter.
- [ ] Specs can define metadata, state-map, archive-gate, derived-issue, and bootstrap contracts from this proposal.
- [ ] Proposal preserves portability by keeping agent logic outside the neutral core.
