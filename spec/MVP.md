# MVP Spec (Week 1)

## Problem
Teams can automate tasks, but they can’t quickly trust or review what agents did.

## Outcome
A daily-operable system where agent actions are transparent, reviewable, and interruptible.

## In Scope (Week 1)
1. Event ingestion API for agent runs
2. Canonical event schema
3. Journal renderer (structured -> readable timeline)
4. Approval gate endpoint + simple UI action
5. One demo workflow end-to-end

## Out of Scope (Week 1)
- Multi-tenant auth hardening
- Advanced role/permission matrices
- Complex analytics dashboards
- Non-core integrations

## Demo Flow
1. Agent starts task `triage_inbox`
2. Emits events (intent, action, outcome)
3. One step flagged `requires_approval=true`
4. UI shows pending approval card
5. Human approves
6. Agent continues and completes
7. Journal shows final summary

## Definition of Done
- Demo flow runs locally in one command
- Journal is understandable by non-engineer reviewer
- Approval action changes runtime state within 2s locally
- Every journal entry links to raw event payload
