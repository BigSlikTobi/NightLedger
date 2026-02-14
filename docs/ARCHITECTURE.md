# Architecture (v0)

## Components
- API service: ingestion + approvals + journal projection
- Web app: timeline + approval UX
- Storage: sqlite (starter) with append-only event table

## Data Shape
- Event stream per run (`run_id` partition)
- Derived journal projection for fast UI reads

## Safety Model
- High-risk events must set `requires_approval=true`
- Runtime pauses on pending approval
- Approval resolution emits explicit `approval_resolved` event
