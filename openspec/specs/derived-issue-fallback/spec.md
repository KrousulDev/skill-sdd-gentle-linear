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

### Requirement: Derived-issue fallback MUST preserve canonical record under partial success
The system MUST keep Engram-backed derived-issue context canonical, SHALL persist per-system outcomes for each attempt, and MUST provide bounded retry/manual fallback when Linear and Engram outcomes diverge.

#### Scenario: Engram success, Linear failure
- GIVEN derived issue is saved in Engram and Linear create fails
- WHEN retry budget is not exhausted
- THEN metadata records partial success with canonical Engram reference
- AND the system retries Linear within bounded policy

#### Scenario: Linear success, Engram follow-up failure
- GIVEN Linear issue is created but Engram linkage update fails
- WHEN attempt finishes
- THEN metadata marks reconciliation-required with both identifiers
- AND the system SHALL return manual/operator instructions without duplicate Linear creation

## Decision Notes (TODO)
- Confirm required manual payload fields and ordering for operator handoff.
