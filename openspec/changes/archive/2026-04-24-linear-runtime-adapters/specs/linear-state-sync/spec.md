# Delta for linear-state-sync

## ADDED Requirements

### Requirement: State sync MUST execute via runtime adapters and persist outcomes
State synchronization MUST call the Linear runtime adapter port, and SHALL persist normalized sync outcomes (`requestedAction`, `observedResult`, `error`) in change metadata.

#### Scenario: Sync success through adapter
- GIVEN a mapped SDD state and runtime adapter available
- WHEN sync is requested
- THEN the core requests mapped status via adapter port
- AND metadata records successful observed Linear status

#### Scenario: Sync adapter failure
- GIVEN mapped status exists but adapter returns an error
- WHEN sync completes
- THEN metadata records requested status and normalized failure outcome
- AND the system returns retryable sync feedback without guessing state
