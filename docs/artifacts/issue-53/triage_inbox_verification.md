# Issue #53 Integration Verification Artifact

Generated on 2026-02-16 (local verification run using FastAPI `TestClient`).

## Scenario

- Run ID: `run_triage_inbox_demo_1`
- Flow: reset seed -> verify paused -> resolve approval -> verify completed

## Evidence snapshot

- pre-approval run status: `status: paused`
- post-approval run status: `status: completed`
- approval response included:
  - `timing.target_ms: 1000`
  - `timing.approval_to_state_update_ms: observed <= timing.target_ms`
  - `timing.within_target: true`
  - `timing.orchestration_receipt_gap_ms: 2`
  - `timing.state_transition: paused->completed`

## Contract assertions

- `approval_to_state_update_ms <= timing.target_ms`
- `within_target == (approval_to_state_update_ms <= timing.target_ms)`
- `orchestration_receipt_gap_ms == 2` for canonical seeded `triage_inbox` flow
- `state_transition == "paused->completed"` for canonical seeded approval

Regenerate with:

- `bash tasks/reset_seed_triage_inbox_demo.sh`
- `./.venv/bin/pytest -q tests/test_triage_inbox_orchestration_api.py`

## Captured responses

```text
reset 200 {'status': 'seeded', 'workflow': 'triage_inbox', 'run_id': 'run_triage_inbox_demo_1', 'event_count': 3, 'seeded_event_ids': ['evt_triage_inbox_001', 'evt_triage_inbox_002', 'evt_triage_inbox_003']}
paused 200 {'run_id': 'run_triage_inbox_demo_1', 'status': 'paused', 'pending_approval': {'event_id': 'evt_triage_inbox_003', 'requested_by': 'agent', 'requested_at': '2026-02-16T08:00:20Z', 'reason': 'Refund amount exceeds policy threshold'}}
approve 200 {'status': 'resolved', 'event_id': 'apr_evt_triage_inbox_003_approved_20260216T205620707716Z_0005d8dd', 'target_event_id': 'evt_triage_inbox_003', 'run_id': 'run_triage_inbox_demo_1', 'decision': 'approved', 'resolved_at': '2026-02-16T20:56:20.707716Z', 'run_status': 'completed', 'orchestration': {'applied': True, 'event_ids': ['evt_triage_inbox_004', 'evt_triage_inbox_005']}, 'timing': {'target_ms': 1000, 'approval_to_state_update_ms': 0, 'within_target': True, 'orchestration_receipt_gap_ms': 2, 'state_transition': 'paused->completed'}}
completed 200 {'run_id': 'run_triage_inbox_demo_1', 'status': 'completed', 'pending_approval': None}
```
