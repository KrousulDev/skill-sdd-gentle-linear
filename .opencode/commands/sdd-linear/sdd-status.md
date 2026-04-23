# /sdd-status

Commands-only packaging is the Fase 1 baseline. This command MUST resolve status from `./.ai/workflows/sdd-linear/state-map.json` and MUST remain operable without `sdd-linear-flow`.

## Managed project-local wrapper

- Core root: `./.ai/workflows/sdd-linear`
- Neutral CLI: `python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py`
- Optional helper: `./.atl/skills/sdd-linear-flow/SKILL.md`

## Execution contract

1. Resolve helper presence.
   - Load `sdd-linear-flow` only if present.
   - If absent, continue and report reduced assistance only.
2. Require `changeId`.
3. Accept optional `sddState` override.
4. Invoke the neutral core:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status \
  --change-id "<change-id>" \
  [--sdd-state "<sdd-state>"]
```

5. Return the JSON emitted by the neutral core as the command result.

## Required behavior

- Read the local SDD state.
- Return the mapped Linear state from declarative config.
- Fail with configuration guidance when no mapping exists.
- Report reduced assistance when the optional helper skill is absent; do not fail the command.
