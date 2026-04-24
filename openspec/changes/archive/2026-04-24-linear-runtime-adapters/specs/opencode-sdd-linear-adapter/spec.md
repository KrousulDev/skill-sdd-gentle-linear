# Delta for opencode-sdd-linear-adapter

## ADDED Requirements

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
- Decide final command UX for explicit live confirmation prompt.
