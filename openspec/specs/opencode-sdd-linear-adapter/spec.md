# opencode-sdd-linear-adapter Specification

## Purpose
Define OpenCode adapter obligations while preserving neutral-core ownership.

## Requirements

### Requirement: OpenCode adapter MUST consume, not own, workflow rules
The adapter MUST read neutral workflow assets from `./.ai/workflows/sdd-linear/`, MUST NOT redefine core business rules in `.atl/` or `.opencode/`, and MUST support optional `sdd-linear-flow` helper presence.

#### Scenario: Happy path with helper skill present
- GIVEN neutral core assets and `sdd-linear-flow` are available
- WHEN an OpenCode command is executed
- THEN the adapter resolves behavior from neutral config/contracts
- AND command output reflects core-driven decisions

#### Scenario: Edge case helper skill absent
- GIVEN `sdd-linear-flow` is not installed
- WHEN OpenCode runs supported SDD commands
- THEN core workflow behavior SHALL still operate
- AND the adapter SHALL report reduced assistance, not functional failure

## Decision Notes (TODO)
- Decide final adapter packaging model: commands only, skill only, or both.
