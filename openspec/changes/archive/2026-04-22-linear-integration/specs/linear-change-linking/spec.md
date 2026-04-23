# linear-change-linking Specification

## Purpose
Define `/sdd-new` linkage and runtime metadata requirements for Linear-backed SDD changes.

## Requirements

### Requirement: `/sdd-new` MUST bind every change to a Linear issue
The system MUST require `linearIssueId` for change creation, MAY accept optional `linearFeatureId`, and MUST persist change metadata under `./.ai/workflows/sdd-linear/changes/`.

#### Scenario: Happy path with issue linkage
- GIVEN interactive mode and a valid `linearIssueId`
- WHEN `/sdd-new` initializes a change
- THEN the change is created with linked issue metadata
- AND metadata is saved in the runtime changes path

#### Scenario: Edge case missing required issue
- GIVEN `/sdd-new` input without `linearIssueId`
- WHEN initialization is requested
- THEN the command SHALL fail with actionable guidance
- AND no change metadata file is created
