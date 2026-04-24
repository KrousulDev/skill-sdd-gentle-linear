# runtime-adapters Specification

## Purpose
Define neutral runtime ports and safe execution modes for Linear/Engram side effects.

## Requirements

### Requirement: Core runtime ports MUST isolate side effects
The core MUST invoke Linear and Engram operations only through explicit runtime adapter ports, and SHALL keep workflow rules independent from vendor/tool-specific payloads.

#### Scenario: Core executes through ports
- GIVEN a workflow step that needs Linear and Engram actions
- WHEN the core executes the step
- THEN it calls adapter ports, not vendor APIs directly
- AND the workflow decision logic remains unchanged by adapter implementation

### Requirement: Runtime mode MUST default to `stub` and require explicit `live` opt-in
The system MUST run in `stub` mode when mode is omitted, MUST require explicit operator/config intent for `live`, and MUST reject unknown modes.

#### Scenario: Default safe mode
- GIVEN runtime mode is not provided
- WHEN a command runs
- THEN adapters run in `stub`
- AND no real Linear/Engram side effect is attempted

#### Scenario: Invalid mode rejected
- GIVEN runtime mode is `"prod"`
- WHEN execution starts
- THEN execution SHALL fail fast with a configuration error

### Requirement: Adapter outcomes MUST be normalized and durably persisted
For each requested action, the system MUST persist `requestedAction`, `observedResult`, and normalized `error` data in local metadata to support retries and reconciliation.

#### Scenario: Partial success across systems
- GIVEN Engram save succeeds and Linear update fails
- WHEN the step completes
- THEN metadata records a partial outcome with both system statuses
- AND retry/fallback logic can continue without losing canonical context

### Requirement: Live mode MUST enforce preflight and smoke safety gates
In `live` mode, the system MUST pass preflight checks (credentials, connectivity, and designated target scope) before side effects, and MUST block high-risk actions unless smoke-safe policy is satisfied.

#### Scenario: Live preflight failure
- GIVEN live mode is requested without valid credentials
- WHEN execution starts
- THEN side effects SHALL NOT run
- AND the system returns actionable preflight diagnostics

## Decision Notes (TODO)
- Decide the finalized normalized error schema fields and enum values.
- Decide first live action scope: comment/update only vs limited close support.
- Decide canonical preflight result schema for wrappers and tests.
