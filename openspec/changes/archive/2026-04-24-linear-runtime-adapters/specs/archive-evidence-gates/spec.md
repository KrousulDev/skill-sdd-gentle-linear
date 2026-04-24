# Delta for archive-evidence-gates

## ADDED Requirements

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
- Decide exact criteria for promoting from comment/update to close in live mode.
