# Architecture (v0)

## Runtime Source of Truth

This document is the canonical runtime-behavior reference for component
responsibilities and layer boundaries.

## Components

- API service (`FastAPI`): ingestion, approvals, status projection, and journal projection API
- Web app (`apps/web`): Vue 3 representation UI over API projections
- Storage: in-memory append-only event table (starter implementation)

## Frontend Representation Layer

- `apps/web/view/index.html` hosts the representation-layer UI shell.
- `apps/web/view/app.js` mounts the Vue app and wires runtime mode + live/demo data.
- `apps/web/model/timeline_model.js` transforms journal payloads into card-ready view models.
- `apps/web/model/mock_data.js` provides deterministic demo-mode fixtures.
- `apps/web/controller/runtime_config.js` resolves `mode/runId/apiBase` runtime inputs.
- `apps/web/controller/api_client.js` handles HTTP boundaries only.
- `apps/web/controller/timeline_controller.js` orchestrates UI state transitions.

## Backend Structure (Modified MVC)

- Controllers (`src/nightledger_api/controllers`): HTTP boundary only
  (routing/status codes; no governance policy).
- Models (`src/nightledger_api/models`): event schema/domain contracts.
- Services (`src/nightledger_api/services`): governance and use-case logic.
- Presenters (`src/nightledger_api/presenters`): deterministic API response shaping.

This maps MVC onto NightLedger separation of concerns:

- Capture layer: controller entrypoint + schema validation.
- Governance layer: service logic (no UI concerns).
- Representation layer: projection/presenter modules (read models only).

## Journal Projection Ownership

- Journal projection ownership belongs to the representation layer.
- Representation code must not enforce governance policy or mutate core state.
- Governance services remain the source of truth for risk/approval transitions.
- Runtime projection is implemented in
  `src/nightledger_api/services/journal_projection_service.py` as a pure
  transformation from ordered `StoredEvent` records to readable entries.

## Data Shape

- Append-only event stream per run (`run_id` partition)
- Derived projections for status/journal read paths

## Safety Model

- High-risk steps can set `requires_approval=true` and `approval.status=pending`.
- Pending approval projects run status to `paused`.
- Resolution is append-only via explicit `approval_resolved` events.
- Terminal lifecycle outcomes are represented by explicit summary/error receipts.
