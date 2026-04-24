# Delta for derived-issue-fallback

## ADDED Requirements

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
- Decide operator UX for reconciliation-required state resolution.
