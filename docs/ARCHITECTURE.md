# Architecture (v0)

## Components
- API service: ingestion + approvals + journal projection
- Web app: timeline + approval UX
- Storage: sqlite (starter) with append-only event table

## Backend Structure (Modified MVC)
- Controllers (`src/nightledger_api/controllers`):
  - HTTP boundary only (routing, request/response codes, no business rules).
- Models (`src/nightledger_api/models`):
  - Event schema/domain types and validation contracts.
- Services (`src/nightledger_api/services`):
  - Governance and use-case logic (capture/gate rules, state transitions).
- Presenters (`src/nightledger_api/presenters`):
  - Deterministic API response shaping (especially error envelopes and projections).

This maps MVC onto NightLedger's separation-of-concerns model:
- Capture Layer: controller + schema validation entrypoint.
- Governance Layer: service logic (no UI concerns).
- Representation Layer: presenter/projection modules (read models only).

## Data Shape
- Event stream per run (`run_id` partition)
- Derived journal projection for fast UI reads

## Safety Model
- High-risk events must set `requires_approval=true`
- Runtime pauses on pending approval
- Approval resolution emits explicit `approval_resolved` event
