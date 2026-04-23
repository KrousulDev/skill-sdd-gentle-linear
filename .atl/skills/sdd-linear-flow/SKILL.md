# Skill: sdd-linear-flow

## Purpose

Provide optional operator guidance for the project-local SDD + Linear adapter without owning workflow rules.

## Core rule

This skill is OPTIONAL. If this file is missing, `/sdd-new`, `/sdd-status`, `/sdd-log-issue`, and `/sdd-archive` MUST still work through the neutral core in `./.ai/workflows/sdd-linear/`.

## Required assets

- Neutral core root: `./.ai/workflows/sdd-linear/`
- Neutral CLI: `python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py`
- Command wrappers: `./.opencode/commands/sdd-linear/*.md`

## Behavior

1. Never redefine workflow rules already declared in the neutral core config, templates, or contracts.
2. Help the operator collect missing inputs before invoking the core CLI.
3. Prefer project-local paths over machine-specific paths.
4. If a required input is missing, ask for it instead of guessing.
5. If Engram save is required for `/sdd-log-issue`, ensure the observation is saved before running the neutral core command.
6. If `/sdd-archive` is blocked, explain which evidence fields are missing and stop there.

## Command guidance

### /sdd-new

- Require `changeId` and `linearIssueId`.
- Accept optional `linearFeatureId`, `title`, `changeType`, `sddState`.
- Run:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new ...
```

### /sdd-status

- Require `changeId`.
- Accept optional `sddState` override.
- Run:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status ...
```

### /sdd-log-issue

- Save to Engram first.
- Then run:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue ...
```

- If the core returns `manual-pending`, present the generated payload and prompt exactly as returned.

### /sdd-archive

- Gather `prUrl`, `mergeConfirmed`, `qaNotes`, and `businessValidation`.
- Then run:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive ...
```

- Do not simulate comment/close when the gate is blocked.
