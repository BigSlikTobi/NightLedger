# Architecture (v0)

## Components
- API service: ingestion + approvals + journal projection
- Web app: Vue 3 timeline + approval UX (representation layer only)
- Storage: sqlite (starter) with append-only event table

## Frontend Representation Layer (Issue #6)
- `apps/web/index.html` hosts a framework-based UI shell.
- `apps/web/app.js` mounts a Vue app and handles loading/error/demo flows.
- `apps/web/timeline_model.js` converts raw journal payloads into display-safe card models.
- `apps/web/mock_data.js` provides demo data when no backend is available (`?runId=demo`).
- `apps/web/journal.test.js` covers the model transformation (empty/error/risk+approval/evidence states).
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

## Journal Projection Ownership
- Journal projection ownership belongs to the representation layer.
- Representation code must not enforce governance policy or mutate core state.
- Governance services remain the source of truth for risk/approval state transitions.
- Runtime projection is implemented in `src/nightledger_api/services/journal_projection_service.py`
  as a pure transformation from ordered `StoredEvent` records to readable entries.

## Data Shape
- Event stream per run (`run_id` partition)
- Derived journal projection for fast UI reads

## Safety Model
- High-risk events must set `requires_approval=true`
- Runtime pauses on pending approval
- Approval resolution emits explicit `approval_resolved` event
