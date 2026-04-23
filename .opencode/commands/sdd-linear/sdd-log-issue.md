# /sdd-log-issue

Commands-only packaging is the Fase 1 baseline. This command MUST use neutral core contracts and MUST remain operable without `sdd-linear-flow`.

## Managed project-local wrapper

- Core root: `./.ai/workflows/sdd-linear`
- Neutral CLI: `python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py`
- Optional helper: `./.atl/skills/sdd-linear-flow/SKILL.md`

## Execution contract

1. Resolve helper presence.
   - Load helper only if installed.
   - If absent, continue and report reduced assistance only.
2. Save the finding to Engram first and capture `engramObservationId`.
3. Require:
   - `changeId`
   - `title`
   - `summary`
   - `blocking`
   - `engramObservationId`
4. Accept optional sync outcome data:
   - `linearIssueId`
   - repeated `attemptError`
   - `impact`
   - `proposedLinearState`
   - repeated `evidenceLink`
   - `operatorNotes`
5. Invoke the neutral core:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue \
  --change-id "<change-id>" \
  --title "<title>" \
  --summary "<summary>" \
  --blocking "<true|false>" \
  --engram-observation-id "<engram-observation-id>" \
  [--impact "<impact>"] \
  [--linear-issue-id "<linear-issue-id>"] \
  [--attempt-error "<attempt-1-error>"] \
  [--attempt-error "<attempt-2-error>"] \
  [--attempt-error "<attempt-3-error>"] \
  [--proposed-linear-state "<linear-state>"] \
  [--evidence-link "<url>"] \
  [--operator-notes "<notes>"]
```

6. Return the JSON emitted by the neutral core. If status is `manual-pending`, surface the generated fallback payload and prompt without additional adapter logic.

## Required behavior

- Save the derived issue to Engram first.
- Retry Linear issue creation up to 3 times.
- Emit manual fallback payload/prompt when retries are exhausted.
- Report reduced assistance when the optional helper skill is absent; do not fail the command.
