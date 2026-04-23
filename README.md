# skill-sdd-gentle-linear

Portable **SDD + Engram + Linear** workflow for project-local usage, with a neutral core, OpenCode command wrappers, an optional helper skill, and bootstrap support for installing the workflow into other repositories.

## Status

- **Phase 1:** implemented and validated
- **Phase 2:** coming soon

Phase 1 focuses on:

- neutral workflow core under `.ai/workflows/sdd-linear/`
- declarative state mapping and contracts
- local change metadata persistence
- OpenCode wrappers under `.opencode/commands/sdd-linear/`
- optional helper skill under `.atl/skills/sdd-linear-flow/`
- idempotent bootstrap script
- automated tests + real manual validation on external sample projects

## Current Runtime

The current Phase 1 implementation uses **`python3`** as the runtime for the neutral core CLI:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py
```

At the moment:

- no `pip` install is required
- no `requirements.txt` is required
- no `pyproject.toml` is required
- standard-library Python is enough for the current workflow and tests

## Project Structure

```text
.
├── .ai/
│   └── workflows/
│       └── sdd-linear/
│           ├── bin/
│           ├── changes/
│           ├── contracts/
│           ├── templates/
│           ├── config.json
│           └── state-map.json
├── .atl/
│   └── skills/
│       └── sdd-linear-flow/
├── .opencode/
│   └── commands/
│       └── sdd-linear/
├── docs/
├── openspec/
├── scripts/
└── tests/
```

## Main Directories

- **`.ai/workflows/sdd-linear/`** — neutral core, contracts, templates, state mapping, runtime metadata path, and Python CLI
- **`.opencode/commands/sdd-linear/`** — OpenCode command wrappers that delegate to the neutral core
- **`.atl/skills/sdd-linear-flow/`** — optional helper skill for operator UX; the core remains usable without it
- **`scripts/`** — bootstrap/install automation
- **`tests/`** — automated validation for Phase 1 behavior
- **`openspec/`** — SDD artifacts and archived change history
- **`docs/`** — human-facing project documentation and validation guides

## Documentation

All current project docs live under [`docs/`](./docs/):

- [`docs/PRD-linear-integration.md`](./docs/PRD-linear-integration.md) — product requirements for the Linear integration
- [`docs/RUNBOOK.md`](./docs/RUNBOOK.md) — manual validation runbook for Phase 1
- [`docs/REAL_TEST_CASES_TEST_REPO.md`](./docs/REAL_TEST_CASES_TEST_REPO.md) — real-world test cases using external sample projects

## How to Use Phase 1

### Run automated tests

```bash
python3 -m unittest discover -s tests -p "test*.py"
```

### Use the neutral core directly

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new --help
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status --help
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue --help
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive --help
```

### Install into another project

```bash
bash ./scripts/bootstrap-sdd-linear.sh <target-path> --dry-run
bash ./scripts/bootstrap-sdd-linear.sh <target-path> --yes
```

After bootstrap:

1. refresh/sync your agent so project-local commands are discovered
2. configure Linear/Engram credentials outside the repo
3. validate `state-map.json` and templates before first real usage

## Validation Evidence

Phase 1 has been validated through:

- automated tests in `tests/`
- SDD verify + archive flow under `openspec/`
- manual real-project validation on external sample repos:
  - `test/codex5.4`
  - `test/spark`

See:

- [`docs/RUNBOOK.md`](./docs/RUNBOOK.md)
- [`docs/REAL_TEST_CASES_TEST_REPO.md`](./docs/REAL_TEST_CASES_TEST_REPO.md)

## Coming Soon — Phase 2

Phase 2 is planned to add **runtime/live integrations** on top of the Phase 1 core:

- real Linear MCP side effects
- real Engram runtime adapters
- stub/live integration modes
- stronger persistence assertions
- end-to-end adapter execution beyond contract/document-level validation

The intention is to keep the **neutral core architecture** intact while adding real infrastructure adapters through explicit ports.
