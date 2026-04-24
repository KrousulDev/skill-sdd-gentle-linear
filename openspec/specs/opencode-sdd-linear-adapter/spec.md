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

### Requirement: OpenCode wrapper MUST select runtime mode and stay thin
The wrapper MUST resolve `runtime.mode` (`stub` default, `live` explicit), SHALL pass mode/preflight context to the core, and MUST NOT implement workflow policy, retry policy, or gate logic.

#### Scenario: Default wrapper behavior
- GIVEN no explicit mode argument
- WHEN an OpenCode SDD command is executed
- THEN wrapper passes `stub` mode to the core
- AND output surfaces adapter outcomes returned by the core

#### Scenario: Live mode invocation
- GIVEN operator requests `live`
- WHEN wrapper invokes the core
- THEN wrapper forwards live intent without mutating workflow rules
- AND wrapper displays preflight/gate failures as returned by core contracts

## Decision Notes (TODO)
- Decide final adapter packaging model: commands only, skill only, or both.
