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

## Decision Notes (TODO)
- Confirm whether Fase 1 archive must revalidate remote Linear state before close.
