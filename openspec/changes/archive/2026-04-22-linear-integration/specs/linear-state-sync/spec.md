# linear-state-sync Specification

## Purpose
Define bounded SDD-to-Linear state synchronization using declarative mapping.

## Requirements

### Requirement: State sync MUST use declarative mapping
The system MUST read SDD→Linear mappings from neutral config, MUST support many SDD states mapping to fewer Linear states in Fase 1, and MUST expose mapped status via `/sdd-status`.

#### Scenario: Happy path mapped status update
- GIVEN a configured `state-map.json` and known SDD state
- WHEN status is synchronized
- THEN the mapped Linear state is selected per config
- AND `/sdd-status` reports both local and mapped states

#### Scenario: Edge case unknown mapping
- GIVEN an SDD state absent from mapping
- WHEN sync is requested
- THEN the system SHALL not guess a hardcoded Linear status
- AND it SHALL return a configuration error for correction
