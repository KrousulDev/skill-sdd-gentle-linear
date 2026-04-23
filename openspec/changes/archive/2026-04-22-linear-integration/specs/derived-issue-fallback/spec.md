# derived-issue-fallback Specification

## Purpose
Define reliable derived-issue handling with Engram-first persistence and Linear fallback.

## Requirements

### Requirement: `/sdd-log-issue` MUST persist first and retry boundedly
In Fase 1, the system MUST require caller evidence that the derived issue was saved to Engram first, MUST record up to 3 Linear creation attempts as contract data, and MUST generate manual creation payload/prompt after 3 failures.

#### Scenario: Happy path success within retry budget
- GIVEN a derived issue is already saved to Engram and carries a canonical `engramObservationId`
- WHEN attempt 1 fails and attempt 2 succeeds in Linear
- THEN the Engram-backed record remains canonical for the workflow
- AND metadata stores the resulting Linear issue reference

#### Scenario: Edge case retries exhausted
- GIVEN all 3 Linear creation attempts fail
- WHEN retry budget is exhausted
- THEN the system SHALL return a complete manual payload/prompt for operator handoff
- AND metadata SHALL mark the item as pending manual creation

## Decision Notes (TODO)
- Confirm required manual payload fields and ordering for operator handoff.
