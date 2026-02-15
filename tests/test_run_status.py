from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.errors import StorageReadError  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402

client = TestClient(app)


def build_event_payload(
    *,
    event_id: str,
    run_id: str,
    timestamp: str,
    event_type: str = "action",
    title: str = "Agent event",
    details: str = "Agent executed a workflow step.",
    requires_approval: bool = False,
    approval_status: str = "not_required",
    requested_by: str | None = None,
    resolved_by: str | None = None,
    resolved_at: str | None = None,
    reason: str | None = None,
    meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": event_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "type": event_type,
        "actor": "agent",
        "title": title,
        "details": details,
        "confidence": 0.8,
        "risk_level": "high" if requires_approval else "low",
        "requires_approval": requires_approval,
        "approval": {
            "status": approval_status,
            "requested_by": requested_by,
            "resolved_by": resolved_by,
            "resolved_at": resolved_at,
            "reason": reason,
        },
        "evidence": [
            {"kind": "log", "label": "Execution log", "ref": "log://status-projection"}
        ],
    }
    if meta is not None:
        payload["meta"] = meta
    return payload


def ingest(payload: dict[str, Any]) -> None:
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 201, response.json()


class _FailingStatusReadStore:
    """Mock EventStore that simulates storage read failures for testing."""
    
    def append(self, event: Any) -> Any:
        """Mock append that returns a dummy stored event."""
        _ = event
        # Return a minimal mock that won't be used in status read tests
        return type('StoredEvent', (), {'id': 'mock', 'integrity_warning': False})()

    def list_by_run_id(self, run_id: str) -> list[Any]:
        """Mock list_by_run_id that always raises StorageReadError."""
        _ = run_id
        raise StorageReadError("storage backend read failed")


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_get_run_status_defaults_to_running_for_non_approval_flow() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_running_1",
            run_id="run_status_running",
            timestamp="2026-02-15T10:00:00Z",
        )
    )

    response = client.get("/v1/runs/run_status_running/status")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_status_running"
    assert body["status"] == "running"
    assert body["pending_approval"] is None


def test_get_run_status_reports_paused_with_pending_approval_context() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_pause_1",
            run_id="run_status_paused",
            timestamp="2026-02-15T11:00:00Z",
            event_type="approval_requested",
            title="Approval required",
            details="Transfer exceeds policy threshold",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Transfer exceeds policy threshold",
        )
    )

    response = client.get("/v1/runs/run_status_paused/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["pending_approval"] == {
        "event_id": "evt_pause_1",
        "requested_by": "agent",
        "requested_at": "2026-02-15T11:00:00Z",
        "reason": "Transfer exceeds policy threshold",
    }


def test_get_run_status_transitions_to_approved_after_resolution() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_approve_req",
            run_id="run_status_approved",
            timestamp="2026-02-15T12:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_approve_resolved",
            run_id="run_status_approved",
            timestamp="2026-02-15T12:01:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            requested_by="agent",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T12:01:00Z",
            reason="Looks safe",
        )
    )

    response = client.get("/v1/runs/run_status_approved/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["pending_approval"] is None


def test_get_run_status_transitions_to_rejected_after_resolution() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_reject_req",
            run_id="run_status_rejected",
            timestamp="2026-02-15T12:10:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_reject_resolved",
            run_id="run_status_rejected",
            timestamp="2026-02-15T12:11:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="rejected",
            requested_by="agent",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T12:11:00Z",
            reason="Violates transfer policy",
        )
    )

    response = client.get("/v1/runs/run_status_rejected/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["pending_approval"] is None


def test_get_run_status_returns_running_after_work_continues_post_approval() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_resume_req",
            run_id="run_status_resumed",
            timestamp="2026-02-15T13:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_resume_resolved",
            run_id="run_status_resumed",
            timestamp="2026-02-15T13:01:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            requested_by="agent",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T13:01:00Z",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_resume_work",
            run_id="run_status_resumed",
            timestamp="2026-02-15T13:02:00Z",
            event_type="action",
            requires_approval=False,
            approval_status="not_required",
            details="Workflow resumed after approval",
        )
    )

    response = client.get("/v1/runs/run_status_resumed/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["pending_approval"] is None


def test_get_run_status_returns_completed_for_summary_terminal_event() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_complete_1",
            run_id="run_status_completed",
            timestamp="2026-02-15T14:00:00Z",
            event_type="summary",
            title="Run completed",
            details="Workflow reached terminal success state",
            requires_approval=False,
            approval_status="not_required",
        )
    )

    response = client.get("/v1/runs/run_status_completed/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["pending_approval"] is None


def test_get_run_status_returns_expired_for_run_expired_terminal_marker() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_expired_1",
            run_id="run_status_expired",
            timestamp="2026-02-15T15:00:00Z",
            event_type="error",
            title="Run expired",
            details="Run exceeded timeout threshold",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            meta={"workflow": "approval_gate", "step": "run_expired"},
        )
    )

    response = client.get("/v1/runs/run_status_expired/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "expired"
    assert body["pending_approval"] is None


def test_get_run_status_returns_expired_for_approval_expired_terminal_marker() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_approval_expired_1",
            run_id="run_status_approval_expired",
            timestamp="2026-02-15T15:10:00Z",
            event_type="error",
            title="Approval expired",
            details="Approval request exceeded timeout threshold",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            meta={"workflow": "approval_gate", "step": "approval_expired"},
        )
    )

    response = client.get("/v1/runs/run_status_approval_expired/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "expired"
    assert body["pending_approval"] is None


def test_get_run_status_returns_stopped_for_run_stopped_terminal_marker() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_stopped_1",
            run_id="run_status_stopped",
            timestamp="2026-02-15T16:00:00Z",
            event_type="error",
            title="Run stopped",
            details="Execution halted after hard policy block",
            requires_approval=False,
            approval_status="not_required",
            meta={"workflow": "approval_gate", "step": "run_stopped"},
        )
    )

    response = client.get("/v1/runs/run_status_stopped/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "stopped"
    assert body["pending_approval"] is None


def test_get_run_status_returns_stopped_for_approval_rejected_terminal_marker() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_approval_rejected_1",
            run_id="run_status_approval_rejected",
            timestamp="2026-02-15T16:10:00Z",
            event_type="error",
            title="Approval rejected",
            details="Approval was rejected by policy",
            requires_approval=True,
            approval_status="rejected",
            requested_by="agent",
            meta={"workflow": "approval_gate", "step": "approval_rejected"},
        )
    )

    response = client.get("/v1/runs/run_status_approval_rejected/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "stopped"
    assert body["pending_approval"] is None


def test_get_run_status_is_deterministic_for_same_event_sequence() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_deterministic_1",
            run_id="run_status_deterministic",
            timestamp="2026-02-15T17:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    first_response = client.get("/v1/runs/run_status_deterministic/status")
    second_response = client.get("/v1/runs/run_status_deterministic/status")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_get_run_status_returns_structured_not_found_for_unknown_run() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    response = client.get("/v1/runs/run_missing_for_status/status")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RUN_NOT_FOUND"
    assert body["error"]["message"] == "Run not found"
    assert body["error"]["details"] == [
        {
            "path": "run_id",
            "message": "No events found for run 'run_missing_for_status'",
            "type": "not_found",
            "code": "RUN_NOT_FOUND",
        }
    ]


def test_get_run_status_returns_structured_storage_read_error() -> None:
    app.dependency_overrides[get_event_store] = lambda: _FailingStatusReadStore()

    response = client.get("/v1/runs/run_status_read_error/status")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_READ_ERROR"
    assert body["error"]["message"] == "Failed to load events"
    assert body["error"]["details"] == [
        {
            "path": "storage",
            "message": "storage backend read failed",
            "type": "storage_failure",
            "code": "STORAGE_READ_FAILED",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_resolution_without_pending() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_inconsistent_1",
            run_id="run_status_inconsistent",
            timestamp="2026-02-15T18:00:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T18:00:00Z",
        )
    )

    response = client.get("/v1/runs/run_status_inconsistent/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["message"] == "Run events contain inconsistent approval state"
    assert body["error"]["details"] == [
        {
            "path": "approval",
            "message": "approval_resolved encountered without pending approval",
            "type": "state_conflict",
            "code": "NO_PENDING_APPROVAL",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_duplicate_resolution() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_dup_resolve_req",
            run_id="run_status_duplicate_resolution",
            timestamp="2026-02-15T19:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_dup_resolve_first",
            run_id="run_status_duplicate_resolution",
            timestamp="2026-02-15T19:01:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T19:01:00Z",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_dup_resolve_second",
            run_id="run_status_duplicate_resolution",
            timestamp="2026-02-15T19:02:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T19:02:00Z",
        )
    )

    response = client.get("/v1/runs/run_status_duplicate_resolution/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"][0]["code"] == "NO_PENDING_APPROVAL"


def test_get_run_status_returns_inconsistent_state_for_invalid_approval_transition() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_invalid_transition_req",
            run_id="run_status_invalid_transition",
            timestamp="2026-02-15T20:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_invalid_transition_resolve",
            run_id="run_status_invalid_transition",
            timestamp="2026-02-15T20:01:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="pending",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T20:01:00Z",
        )
    )

    response = client.get("/v1/runs/run_status_invalid_transition/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "approval.status",
            "message": "approval_resolved must use approved or rejected status",
            "type": "state_conflict",
            "code": "INVALID_APPROVAL_TRANSITION",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_events_after_terminal() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_terminal_done",
            run_id="run_status_terminal_conflict",
            timestamp="2026-02-15T21:00:00Z",
            event_type="summary",
            title="Run completed",
            details="Completed successfully",
            requires_approval=False,
            approval_status="not_required",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_terminal_after",
            run_id="run_status_terminal_conflict",
            timestamp="2026-02-15T21:01:00Z",
            event_type="action",
            details="Action emitted after completion marker",
            requires_approval=False,
            approval_status="not_required",
        )
    )

    response = client.get("/v1/runs/run_status_terminal_conflict/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "workflow_status",
            "message": "event stream continued after terminal status 'completed'",
            "type": "state_conflict",
            "code": "TERMINAL_STATE_CONFLICT",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_duplicate_pending_approvals() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_pending_dup_1",
            run_id="run_status_duplicate_pending",
            timestamp="2026-02-15T22:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Initial approval gate",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_pending_dup_2",
            run_id="run_status_duplicate_pending",
            timestamp="2026-02-15T22:01:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Second pending approval before first resolved",
        )
    )

    response = client.get("/v1/runs/run_status_duplicate_pending/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "approval",
            "message": "multiple pending approvals encountered without resolution",
            "type": "state_conflict",
            "code": "DUPLICATE_PENDING_APPROVAL",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_missing_approver_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_missing_approver_req",
            run_id="run_status_missing_approver",
            timestamp="2026-02-15T22:10:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_missing_approver_resolved",
            run_id="run_status_missing_approver",
            timestamp="2026-02-15T22:11:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            resolved_by=None,
            resolved_at="2026-02-15T22:11:00Z",
        )
    )

    response = client.get("/v1/runs/run_status_missing_approver/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "approval.resolved_by",
            "message": "approval_resolved is missing approver identity",
            "type": "state_conflict",
            "code": "MISSING_APPROVER_ID",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_missing_approval_timestamp() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_missing_timestamp_req",
            run_id="run_status_missing_timestamp",
            timestamp="2026-02-15T22:20:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_missing_timestamp_resolved",
            run_id="run_status_missing_timestamp",
            timestamp="2026-02-15T22:21:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            resolved_by="human_reviewer",
            resolved_at=None,
        )
    )

    response = client.get("/v1/runs/run_status_missing_timestamp/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "approval.resolved_at",
            "message": "approval_resolved is missing resolution timestamp",
            "type": "state_conflict",
            "code": "MISSING_APPROVAL_TIMESTAMP",
        }
    ]


def test_get_run_status_returns_inconsistent_state_for_events_after_rejection() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_reject_conflict_req",
            run_id="run_status_reject_conflict",
            timestamp="2026-02-15T22:30:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_reject_conflict_resolved",
            run_id="run_status_reject_conflict",
            timestamp="2026-02-15T22:31:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="rejected",
            resolved_by="human_reviewer",
            resolved_at="2026-02-15T22:31:00Z",
            reason="Rejected by policy",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_reject_conflict_after",
            run_id="run_status_reject_conflict",
            timestamp="2026-02-15T22:32:00Z",
            event_type="action",
            requires_approval=False,
            approval_status="not_required",
            details="Run continued after rejection",
        )
    )

    response = client.get("/v1/runs/run_status_reject_conflict/status")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"] == [
        {
            "path": "workflow_status",
            "message": "event stream continued after rejection without terminal stop",
            "type": "state_conflict",
            "code": "REJECTED_STATE_CONFLICT",
        }
    ]
