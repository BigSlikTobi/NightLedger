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

## Data Shape
- Event stream per run (`run_id` partition)
- Derived journal projection for fast UI reads

## Safety Model
- High-risk events must set `requires_approval=true`
- Runtime pauses on pending approval
- Approval resolution emits explicit `approval_resolved` event
