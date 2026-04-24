# /sdd-new

Commands-only packaging is the Fase 1 baseline. This command MUST read neutral assets from `./.ai/workflows/sdd-linear/` and MUST remain operable without `sdd-linear-flow`.

## Managed project-local wrapper

- Core root: `./.ai/workflows/sdd-linear`
- Neutral CLI: `python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py`
- Optional helper: `./.atl/skills/sdd-linear-flow/SKILL.md`

## Execution contract

1. Resolve helper presence.
   - If `./.atl/skills/sdd-linear-flow/SKILL.md` exists, load it for UX guidance only.
   - If it is absent, continue normally and state that helper assistance is unavailable.
2. Validate required input:
   - `changeId`
   - `linearIssueId`
3. Accept optional input:
    - `linearFeatureId`
    - `title`
    - `changeType`
    - `sddState`
    - `runtimeMode` (`stub` default, `live` only with explicit confirmation)
    - `liveConfirmation` (required phrase: `ALLOW_SDD_LINEAR_LIVE` when `runtimeMode=live`)
4. Invoke the neutral core instead of reimplementing workflow rules:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id "<change-id>" \
  --linear-issue-id "<linear-issue-id>" \
  [--linear-feature-id "<linear-feature-id>"] \
  [--title "<title>"] \
  [--change-type "<change-type>"] \
  [--sdd-state "<sdd-state>"] \
  [--runtime-mode "<stub|live>"]
```

5. Return the JSON emitted by the neutral core as the command result.

## Live mode confirmation UX

- Default to `runtimeMode=stub` when the operator does not choose a mode.
- If the operator requests `live`, require the exact confirmation phrase `ALLOW_SDD_LINEAR_LIVE` before passing `--runtime-mode live` to the core.
- Do not add workflow logic, prompts, or mutations beyond capturing that explicit confirmation and passing the chosen mode through.

## Required behavior

- Require `linearIssueId`.
- Accept optional `linearFeatureId`.
- Persist change metadata under `./.ai/workflows/sdd-linear/changes/{change}.json`.
- Report reduced assistance when the optional helper skill is absent; do not fail the command.
