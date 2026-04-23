## Exploration: linear-integration

### Current State
This repository is greenfield and document-first. The only verified project artifact is `PRD-linear-integration.md`; there is no implementation code, no existing OpenSpec structure, and no runtime workflow assets yet. The PRD already fixes the core Fase 1 constraints: Linear is mandatory, runtime change metadata lives in `./.ai/workflows/sdd-linear/changes/`, many SDD states must map to fewer Linear states, archive requires minimum evidence, derived issues must always be recorded in Engram, and `sdd-linear-flow` is an optional agent helper rather than part of the neutral core.

### Affected Areas
- `PRD-linear-integration.md` — source of truth for current requirements and unresolved questions.
- `openspec/changes/linear-integration/exploration.md` — exploration artifact for this change.
- `./.ai/workflows/sdd-linear/` — planned neutral core root.
- `./.ai/workflows/sdd-linear/config.json` — planned integration and policy config.
- `./.ai/workflows/sdd-linear/state-map.json` — planned declarative SDD→Linear state mapping.
- `./.ai/workflows/sdd-linear/changes/` — planned runtime metadata store for per-change state.
- `./.ai/workflows/sdd-linear/templates/` — planned templates for Linear comments and fallback payloads.
- `.atl/` and/or `.opencode/` — planned agent adapter surface for OpenCode/gentle-ai.
- `scripts/bootstrap-sdd-linear.sh` — planned portable installer/bootstrap entry point.

### Approaches
1. **Core-first neutral domain** — define portable workflow contracts first, then add the OpenCode adapter on top.
   - Pros: preserves multi-agent architecture, keeps Linear rules/config in one source of truth, reduces vendor lock-in.
   - Cons: slightly more upfront design work before command wiring.
   - Effort: Medium.

2. **Adapter-first OpenCode implementation** — start inside `.atl/`/`.opencode/` and infer the core later.
   - Pros: faster first demo for one agent.
   - Cons: high risk of hardcoding agent assumptions, duplicated logic later, weaker portability.
   - Effort: Low initially / High later.

### Recommendation
Use **Core-first neutral domain** for Fase 1, but keep the scope deliberately narrow. Implement only the minimum backbone needed to prove the workflow: declarative config, state mapping, per-change metadata persistence, derived-issue logging contract, archive gate validation contract, and one OpenCode adapter that consumes that core. Leave feature-close automation, richer state rollout, and advanced UX/TUI work for later phases.

### Fase 1 Scope Clarification
- **In scope**
  - Neutral folder structure under `./.ai/workflows/sdd-linear/`.
  - Declarative config contract for Linear integration, archive policy, and templates.
  - External `state-map.json` supporting many SDD states mapped into a small initial Linear state set.
  - Runtime change metadata model in `./.ai/workflows/sdd-linear/changes/`.
  - Derived-issue flow contract: Engram save first, Linear create/update with up to 3 retries, then manual payload fallback.
  - Archive evidence contract with minimum Fase 1 gates: PR URL, merge confirmed, QA notes, business validation.
  - One OpenCode/gentle-ai adapter and the existence contract for `sdd-linear-flow`.
  - Bootstrap design sufficient to install/regenerate the neutral core plus initial adapter.
- **Out of scope for Fase 1**
  - Full automation of feature/project close.
  - Rich custom TUI.
  - Multi-agent adapters beyond OpenCode.
  - Deep Linear workspace provisioning beyond the minimum initial state mapping/rollout support.

### Major Components and Boundaries
- **Neutral Workflow Core**: owns workflow rules, config parsing, change metadata schema, gate evaluation, and integration contracts.
- **Linear Integration Boundary**: owns issue/project lookup, state sync, comments, and close actions; should be replaceable behind a port/bridge.
- **Engram Persistence Boundary**: owns historical memory obligations, especially derived issue logging and final summaries.
- **Agent Adapter Boundary**: translates agent/slash-command behavior into neutral core operations; no business rules should live here.
- **Bootstrap Boundary**: installs/syncs assets safely, but never becomes the source of truth.
- **Evidence/Template Boundary**: renders structured comments, archive summaries, and manual fallback payloads from declarative templates.

### Open Decisions That Still Matter Before Proposal/Spec
- Exact initial Linear status names to target in Fase 1 state mapping.
- Exact schema for change metadata files (single JSON per change vs richer nested evidence structure).
- Exact manual fallback payload format for failed derived-issue creation.
- Whether archive validation is purely local/config-driven in Fase 1 or also revalidates remote Linear state before close.
- Whether the OpenCode adapter is implemented as project-local commands, skill instructions, or both.
- Whether bootstrap should copy a full template snapshot or sync only managed workflow paths.

### Pragmatic Sequencing Strategy
1. Define the neutral filesystem contract and configuration artifacts first.
2. Write the proposal around that bounded Fase 1 backbone only.
3. Spec the metadata schema, state-map behavior, archive gates, and derived-issue fallback behavior.
4. Design the integration ports: Linear bridge, Engram persistence hooks, adapter interface, bootstrap contract.
5. Implement the neutral core artifacts before any agent-specific polish.
6. Add the OpenCode adapter and `sdd-linear-flow` support on top of the stable contracts.
7. Leave bootstrap script implementation near the end of Fase 1 once core paths and managed assets are fixed.

### Risks
- Fase 1 can sprawl if feature-close and workspace-state provisioning are not explicitly deferred.
- Hardcoding Linear states too early will break portability across workspaces.
- Mixing agent behavior into the neutral core will undermine the repo’s main architectural goal.
- Archive gates may look complete on paper but stay weak if evidence schema is underspecified.

### Ready for Proposal
Yes — the change is ready for proposal if the next phase explicitly treats Fase 1 as a narrow core-first integration slice and resolves the remaining high-impact decisions above in proposal/spec language.
