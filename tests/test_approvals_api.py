from pathlib import Path
import logging
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
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
    risk_level: str | None = None,
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
        "risk_level": risk_level if risk_level is not None else ("high" if requires_approval else "low"),
        "requires_approval": requires_approval,
        "approval": {
            "status": approval_status,
            "requested_by": requested_by,
            "resolved_by": resolved_by,
            "resolved_at": resolved_at,
            "reason": reason,
        },
        "evidence": [
            {"kind": "log", "label": "Execution log", "ref": "log://approval-api"}
        ],
    }
    return payload


def ingest(payload: dict[str, Any]) -> None:
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 201, response.json()


class _FailingApprovalAppendStore:
    def __init__(self) -> None:
        self._base = InMemoryAppendOnlyEventStore()

    def append(self, event: Any) -> Any:
        if getattr(event, "type", None) == "approval_resolved":
            raise RuntimeError("storage backend append failed")
        return self._base.append(event)

    def list_by_run_id(self, run_id: str) -> list[Any]:
        return self._base.list_by_run_id(run_id)

    def list_all(self) -> list[Any]:
        return self._base.list_all()


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_get_pending_approvals_returns_unresolved_pending_events() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_pending_1",
            run_id="run_pending_1",
            timestamp="2026-02-16T09:00:00Z",
            event_type="approval_requested",
            title="Approval required",
            details="Transfer exceeds threshold",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Transfer exceeds threshold",
            risk_level="high",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_running_1",
            run_id="run_running_1",
            timestamp="2026-02-16T09:01:00Z",
            event_type="action",
            requires_approval=False,
            approval_status="not_required",
            risk_level="low",
        )
    )

    response = client.get("/v1/approvals/pending")

    assert response.status_code == 200
    body = response.json()
    assert body["pending_count"] == 1
    assert len(body["approvals"]) == 1
    assert body["approvals"][0] == {
        "event_id": "evt_pending_1",
        "decision_id": None,
        "run_id": "run_pending_1",
        "requested_at": "2026-02-16T09:00:00Z",
        "requested_by": "agent",
        "title": "Approval required",
        "details": "Transfer exceeds threshold",
        "reason": "Transfer exceeds threshold",
        "risk_level": "high",
    }


def test_post_approval_resolves_pending_request_with_approved_decision() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_approve_target",
            run_id="run_approve_target",
            timestamp="2026-02-16T10:00:00Z",
            event_type="approval_requested",
            title="Approval required",
            details="Transfer exceeds threshold",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Transfer exceeds threshold",
        )
    )

    response = client.post(
        "/v1/approvals/evt_approve_target",
        json={"decision": "approved", "approver_id": "human_approver", "reason": "Looks safe"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["target_event_id"] == "evt_approve_target"
    assert body["run_id"] == "run_approve_target"
    assert body["decision"] == "approved"
    assert isinstance(body["event_id"], str) and body["event_id"]
    assert body["resolved_at"].endswith("Z")

    status_response = client.get("/v1/runs/run_approve_target/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "approved"
    assert status_response.json()["pending_approval"] is None

    pending_response = client.get("/v1/approvals/pending")
    assert pending_response.status_code == 200
    assert pending_response.json()["pending_count"] == 0


def test_post_approval_resolves_pending_request_with_rejected_decision() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_reject_target",
            run_id="run_reject_target",
            timestamp="2026-02-16T11:00:00Z",
            event_type="approval_requested",
            title="Approval required",
            details="Delete action requires sign-off",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="Delete action requires sign-off",
        )
    )

    response = client.post(
        "/v1/approvals/evt_reject_target",
        json={
            "decision": "rejected",
            "approver_id": "human_reviewer",
            "reason": "Policy does not allow this action",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["decision"] == "rejected"

    status_response = client.get("/v1/runs/run_reject_target/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "stopped"


def test_post_approval_returns_not_found_for_unknown_target_event() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    response = client.post(
        "/v1/approvals/evt_unknown_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "APPROVAL_NOT_FOUND"


def test_post_approval_rejects_duplicate_resolution_for_same_target() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_duplicate_resolution_target",
            run_id="run_duplicate_resolution_target",
            timestamp="2026-02-16T12:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    first_response = client.post(
        "/v1/approvals/evt_duplicate_resolution_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/v1/approvals/evt_duplicate_resolution_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )
    assert second_response.status_code == 409
    body = second_response.json()
    assert body["error"]["code"] == "DUPLICATE_APPROVAL"
    assert body["error"]["rule_ids"] == ["RULE-GATE-003"]


def test_post_approval_rejects_target_that_is_not_pending_approval() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_not_pending_target",
            run_id="run_not_pending_target",
            timestamp="2026-02-16T12:10:00Z",
            event_type="action",
            requires_approval=False,
            approval_status="not_required",
        )
    )

    response = client.post(
        "/v1/approvals/evt_not_pending_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "NO_PENDING_APPROVAL"
    assert body["error"]["rule_ids"] == ["RULE-GATE-002"]


def test_post_approval_rejects_ambiguous_event_id_across_runs() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_shared_pending",
            run_id="run_alpha",
            timestamp="2026-02-16T13:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_shared_pending",
            run_id="run_beta",
            timestamp="2026-02-16T13:01:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_shared_pending",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "AMBIGUOUS_EVENT_ID"


def test_get_pending_approvals_surfaces_inconsistent_run_state() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_pending_inconsistent",
            run_id="run_pending_inconsistent",
            timestamp="2026-02-16T14:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    ingest(
        build_event_payload(
            event_id="evt_pending_inconsistent_second",
            run_id="run_pending_inconsistent",
            timestamp="2026-02-16T14:01:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.get("/v1/approvals/pending")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"][0]["code"] == "DUPLICATE_PENDING_APPROVAL"


def test_post_approval_returns_duplicate_for_stale_resolved_target_with_new_pending() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_stale_target",
            run_id="run_stale_target",
            timestamp="2026-02-16T15:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    first_resolution = client.post(
        "/v1/approvals/evt_stale_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )
    assert first_resolution.status_code == 200

    ingest(
        build_event_payload(
            event_id="evt_new_pending_target",
            run_id="run_stale_target",
            timestamp="2026-02-16T15:02:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    stale_response = client.post(
        "/v1/approvals/evt_stale_target",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert stale_response.status_code == 409
    body = stale_response.json()
    assert body["error"]["code"] == "DUPLICATE_APPROVAL"
    assert body["error"]["rule_ids"] == ["RULE-GATE-003"]


def test_post_approval_rejects_whitespace_only_approver_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_whitespace_approver_target",
            run_id="run_whitespace_approver_target",
            timestamp="2026-02-16T16:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_whitespace_approver_target",
        json={"decision": "approved", "approver_id": "   "},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["error"]["message"] == "Approval request payload failed validation"
    assert body["error"]["rule_ids"] == ["RULE-GATE-007"]
    assert body["error"]["details"] == [
        {
            "path": "approver_id",
            "message": "String should have at least 1 character",
            "type": "string_too_short",
            "code": "MISSING_APPROVER_ID",
        }
    ]


def test_post_approval_rejects_invalid_decision_with_structured_envelope() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_invalid_decision_target",
            run_id="run_invalid_decision_target",
            timestamp="2026-02-16T16:05:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_invalid_decision_target",
        json={"decision": "accept", "approver_id": "human_approver"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["error"]["message"] == "Approval request payload failed validation"
    assert body["error"]["rule_ids"] == ["RULE-GATE-004"]
    assert body["error"]["details"] == [
        {
            "path": "decision",
            "message": "Input should be 'approved' or 'rejected'",
            "type": "literal_error",
            "code": "INVALID_APPROVAL_DECISION",
        }
    ]


def test_post_approval_rejects_missing_approver_with_structured_envelope() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_missing_approver_target",
            run_id="run_missing_approver_target",
            timestamp="2026-02-16T16:06:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_missing_approver_target",
        json={"decision": "approved"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["error"]["message"] == "Approval request payload failed validation"
    assert body["error"]["rule_ids"] == ["RULE-GATE-007"]
    assert body["error"]["details"] == [
        {
            "path": "approver_id",
            "message": "Field required",
            "type": "missing",
            "code": "MISSING_APPROVER_ID",
        }
    ]


def test_post_approval_returns_storage_write_error_on_resolution_append_failure() -> None:
    store = _FailingApprovalAppendStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_resolution_append_fail",
            run_id="run_resolution_append_fail",
            timestamp="2026-02-16T16:10:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_resolution_append_fail",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_WRITE_ERROR"


def test_post_approval_logs_structured_approved_resolution(caplog) -> None:
    caplog.set_level(logging.INFO, logger="nightledger_api.controllers.events_controller")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_log_approved",
            run_id="run_log_approved",
            timestamp="2026-02-16T17:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_log_approved",
        json={"decision": "approved", "approver_id": "human_approver"},
    )

    assert response.status_code == 200
    assert any(
        '"event": "approval_resolution_completed"' in record.message
        and '"decision": "approved"' in record.message
        and '"approver_id": "human_approver"' in record.message
        for record in caplog.records
    )


def test_post_approval_logs_structured_rejected_resolution(caplog) -> None:
    caplog.set_level(logging.INFO, logger="nightledger_api.controllers.events_controller")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_log_rejected",
            run_id="run_log_rejected",
            timestamp="2026-02-16T17:10:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_log_rejected",
        json={"decision": "rejected", "approver_id": "human_reviewer"},
    )

    assert response.status_code == 200
    assert any(
        '"event": "approval_resolution_completed"' in record.message
        and '"decision": "rejected"' in record.message
        and '"approver_id": "human_reviewer"' in record.message
        for record in caplog.records
    )


def test_post_approval_logs_structured_completion_to_uvicorn_logger(caplog) -> None:
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_log_uvicorn",
            run_id="run_log_uvicorn",
            timestamp="2026-02-16T17:20:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )

    response = client.post(
        "/v1/approvals/evt_log_uvicorn",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )

    assert response.status_code == 200
    assert any(
        '"event": "approval_resolution_completed"' in record.message
        and '"decision": "approved"' in record.message
        and '"approver_id": "human_reviewer"' in record.message
        for record in caplog.records
    )


def test_issue46_round1_registers_pending_approval_by_decision_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    response = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round1",
            "run_id": "run_issue46_round1",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "registered"
    assert body["decision_id"] == "dec_issue46_round1"
    assert body["run_id"] == "run_issue46_round1"
    assert body["approval_status"] == "pending"
    assert isinstance(body["event_id"], str) and body["event_id"]

    pending = client.get("/v1/approvals/pending")
    assert pending.status_code == 200
    pending_body = pending.json()
    assert pending_body["pending_count"] == 1
    assert pending_body["approvals"][0]["decision_id"] == "dec_issue46_round1"


def test_issue46_round2_resolves_pending_approval_by_decision_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    register_response = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round2",
            "run_id": "run_issue46_round2",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_response.status_code == 200

    resolve_response = client.post(
        "/v1/approvals/decisions/dec_issue46_round2",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for execution",
        },
    )

    assert resolve_response.status_code == 200
    body = resolve_response.json()
    assert body["status"] == "resolved"
    assert body["decision_id"] == "dec_issue46_round2"
    assert body["decision"] == "approved"
    assert body["run_id"] == "run_issue46_round2"


def test_issue46_round3_queries_decision_id_approval_state() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    register_response = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round3",
            "run_id": "run_issue46_round3",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_response.status_code == 200

    query_response = client.get("/v1/approvals/decisions/dec_issue46_round3")
    assert query_response.status_code == 200
    body = query_response.json()
    assert body["decision_id"] == "dec_issue46_round3"
    assert body["run_id"] == "run_issue46_round3"
    assert body["status"] == "pending"
    assert body["resolved_event_id"] is None
    assert body["resolved_at"] is None


def test_issue46_round4_rejects_duplicate_late_resolution_by_decision_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    register_response = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round4",
            "run_id": "run_issue46_round4",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_response.status_code == 200

    first = client.post(
        "/v1/approvals/decisions/dec_issue46_round4",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/approvals/decisions/dec_issue46_round4",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "DUPLICATE_APPROVAL"


def test_issue46_round4_query_unknown_decision_id_returns_not_found() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    response = client.get("/v1/approvals/decisions/dec_issue46_unknown")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "APPROVAL_NOT_FOUND"
    assert body["error"]["details"][0]["path"] == "decision_id"


def test_issue46_round5_rejects_duplicate_pending_registration_by_decision_id() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    first = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round5_dup",
            "run_id": "run_issue46_round5_dup",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round5_dup",
            "run_id": "run_issue46_round5_dup",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "DUPLICATE_APPROVAL"
    assert body["error"]["message"] == "Approval already pending"
    assert body["error"]["details"][0]["message"] == (
        "Approval for decision 'dec_issue46_round5_dup' is already pending"
    )


def test_issue46_round5_query_returns_resolved_state_after_decision_resolution() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    register_response = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_issue46_round5_query",
            "run_id": "run_issue46_round5_query",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_response.status_code == 200
    resolve_response = client.post(
        "/v1/approvals/decisions/dec_issue46_round5_query",
        json={"decision": "rejected", "approver_id": "human_reviewer"},
    )
    assert resolve_response.status_code == 200

    query_response = client.get("/v1/approvals/decisions/dec_issue46_round5_query")
    assert query_response.status_code == 200
    body = query_response.json()
    assert body["status"] == "rejected"
    assert body["resolved_event_id"] is not None
    assert body["resolved_by"] == "human_reviewer"
    assert body["resolved_at"] is not None


def test_issue46_round5_legacy_event_id_route_remains_supported() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    ingest(
        build_event_payload(
            event_id="evt_issue46_legacy_target",
            run_id="run_issue46_legacy_target",
            timestamp="2026-02-18T10:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
        )
    )
    response = client.post(
        "/v1/approvals/evt_issue46_legacy_target",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert response.status_code == 200
    assert response.json()["target_event_id"] == "evt_issue46_legacy_target"
