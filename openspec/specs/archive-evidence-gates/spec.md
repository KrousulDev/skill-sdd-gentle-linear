# archive-evidence-gates Specification

## Purpose
Define minimum archive evidence gates and close behavior for `/sdd-archive`.

## Requirements

### Requirement: `/sdd-archive` MUST block on missing minimum evidence
In Fase 1, the system MUST require `prUrl`, `mergeConfirmed`, `qaNotes`, and `businessValidation` before archive actions, MUST record gate evaluation in change metadata, and SHALL stop archive on any missing required field.

#### Scenario: Happy path archive completion
- GIVEN all minimum evidence fields are present and valid
- WHEN `/sdd-archive` is executed
- THEN the system renders a structured completion comment for Linear
- AND it MAY mark the linked issue as close-eligible per configured policy

#### Scenario: Edge case missing evidence
- GIVEN `qaNotes` is missing
- WHEN `/sdd-archive` is executed
- THEN archive is blocked with explicit missing-field feedback
- AND no close-eligible action is emitted by the Fase 1 contract

### Requirement: Archive flow MUST gate live side effects using adapter outcomes
When archive runs in `live` mode, the system MUST record adapter outcomes in metadata and MUST block close/high-risk actions unless evidence gates and smoke-safe policy both pass.

#### Scenario: Live close blocked
- GIVEN required archive evidence is present but smoke-safe target policy fails
- WHEN `/sdd-archive` attempts close behavior in live mode
- THEN close action SHALL be blocked
- AND metadata stores gate result and blocked adapter outcome

#### Scenario: Live archive comment allowed
- GIVEN evidence gates pass and smoke-safe policy allows non-destructive action
- WHEN `/sdd-archive` runs in live mode
- THEN comment/update side effects MAY execute through adapters
- AND metadata records observed adapter results for audit

## Decision Notes (TODO)
- Confirm whether Fase 1 archive must revalidate remote Linear state before close.
