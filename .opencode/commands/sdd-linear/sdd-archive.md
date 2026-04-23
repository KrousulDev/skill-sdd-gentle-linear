# /sdd-archive

Commands-only packaging is the Fase 1 baseline. This command MUST use neutral core assets from `./.ai/workflows/sdd-linear/` and MUST remain operable without `sdd-linear-flow`.

## Managed project-local wrapper

- Core root: `./.ai/workflows/sdd-linear`
- Neutral CLI: `python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py`
- Optional helper: `./.atl/skills/sdd-linear-flow/SKILL.md`

## Execution contract

1. Resolve helper presence.
   - Load helper only if installed.
   - If absent, continue and report reduced assistance only.
2. Require `changeId`.
3. Accept archive evidence fields:
   - `prUrl`
   - `mergeConfirmed`
   - `qaNotes`
   - `businessValidation`
   - `archiveSummary`
   - `followUpNotes`
4. Invoke the neutral core:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id "<change-id>" \
  [--pr-url "<pr-url>"] \
  [--merge-confirmed "<true|false>"] \
  [--qa-notes "<qa-notes>"] \
  [--business-validation "<business-validation>"] \
  [--archive-summary "<archive-summary>"] \
  [--follow-up-notes "<follow-up-notes>"]
```

5. Return the JSON emitted by the neutral core. When the gate is blocked, surface missing evidence and do not add adapter-side close/comment behavior.

## Archive policy

- Required evidence: `prUrl`, `mergeConfirmed`, `qaNotes`, `businessValidation`.
- Remote Linear revalidation is **disabled in Fase 1**; the local evidence gate is canonical.
- Comment and close actions are blocked whenever the evidence gate fails.
- Report reduced assistance when the optional helper skill is absent; do not fail the command.
