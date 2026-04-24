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
4. Accept optional runtime controls:
   - `runtimeMode` (`stub` default)
   - `liveConfirmation` (required phrase: `ALLOW_SDD_LINEAR_LIVE` when `runtimeMode=live`)
5. Invoke the neutral core:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status \
  --change-id "<change-id>" \
  [--sdd-state "<sdd-state>"] \
  [--runtime-mode "<stub|live>"]
```

6. Return the JSON emitted by the neutral core as the command result.

## Live mode confirmation UX

- Default to `runtimeMode=stub` when omitted.
- If the operator requests `live`, require the exact confirmation phrase `ALLOW_SDD_LINEAR_LIVE` before forwarding `--runtime-mode live`.
- Surface preflight failures and adapter outcomes exactly as returned by the core JSON.

## Required behavior

- Read the local SDD state.
- Return the mapped Linear state from declarative config.
- Fail with configuration guidance when no mapping exists.
- Report reduced assistance when the optional helper skill is absent; do not fail the command.
