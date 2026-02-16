from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402


client = TestClient(app)


def test_round1_triage_inbox_approval_resume_reaches_terminal_completed_state() -> None:
    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    paused_response = client.get("/v1/runs/run_triage_inbox_demo_1/status")
    assert paused_response.status_code == 200
    assert paused_response.json()["status"] == "paused"

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    completed_response = client.get("/v1/runs/run_triage_inbox_demo_1/status")
    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert completed_response.json()["pending_approval"] is None


def test_round2_triage_inbox_approval_response_surfaces_transition_receipts() -> None:
    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    body = approve_response.json()
    assert body["run_status"] == "completed"
    assert body["orchestration"] == {
        "applied": True,
        "event_ids": ["evt_triage_inbox_004", "evt_triage_inbox_005"],
    }


def test_round3_orchestration_append_failure_is_structured_and_journaled() -> None:
    class _FailingOrchestrationAppendStore:
        def __init__(self) -> None:
            self._base = InMemoryAppendOnlyEventStore()

        def append(self, event: object) -> object:
            if getattr(event, "id", None) == "evt_triage_inbox_004":
                raise RuntimeError("orchestration append exploded")
            return self._base.append(event)

        def list_by_run_id(self, run_id: str) -> list[object]:
            return self._base.list_by_run_id(run_id)

        def list_all(self) -> list[object]:
            return self._base.list_all()

    store = _FailingOrchestrationAppendStore()
    app.dependency_overrides[get_event_store] = lambda: store
    try:
        ingest_response = client.post(
            "/v1/events",
            json={
                "id": "evt_triage_inbox_003",
                "run_id": "run_triage_inbox_demo_1",
                "timestamp": "2026-02-16T08:00:20Z",
                "type": "approval_requested",
                "actor": "agent",
                "title": "Approval required before sending refund",
                "details": "Refund exceeds threshold and requires sign-off.",
                "confidence": 0.81,
                "risk_level": "high",
                "requires_approval": True,
                "approval": {
                    "status": "pending",
                    "requested_by": "agent",
                    "resolved_by": None,
                    "resolved_at": None,
                    "reason": "Refund amount exceeds policy threshold",
                },
                "evidence": [
                    {
                        "kind": "artifact",
                        "label": "Refund request packet",
                        "ref": "artifact://triage-inbox/003",
                    }
                ],
                "meta": {"workflow": "triage_inbox", "step": "approval_gate"},
            },
        )
        assert ingest_response.status_code == 201

        approve_response = client.post(
            "/v1/approvals/evt_triage_inbox_003",
            json={
                "decision": "approved",
                "approver_id": "human_reviewer",
                "reason": "Approved for demo completion",
            },
        )
        assert approve_response.status_code == 500
        assert approve_response.json()["error"]["code"] == "STORAGE_WRITE_ERROR"
        assert (
            approve_response.json()["error"]["details"][0]["message"]
            == "triage_inbox orchestration append failed"
        )

        status_response = client.get("/v1/runs/run_triage_inbox_demo_1/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "stopped"

        events_response = client.get("/v1/runs/run_triage_inbox_demo_1/events")
        assert events_response.status_code == 200
        event_types = [item["payload"]["type"] for item in events_response.json()["events"]]
        assert "error" in event_types
    finally:
        app.dependency_overrides.clear()


def test_round5_orchestration_applies_only_to_canonical_triage_demo_approval() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    try:
        ingest_response = client.post(
            "/v1/events",
            json={
                "id": "evt_triage_inbox_custom_pending",
                "run_id": "run_triage_inbox_demo_1",
                "timestamp": "2026-02-16T09:00:00Z",
                "type": "approval_requested",
                "actor": "agent",
                "title": "Custom approval required",
                "details": "Custom pending event in demo run.",
                "confidence": 0.7,
                "risk_level": "high",
                "requires_approval": True,
                "approval": {
                    "status": "pending",
                    "requested_by": "agent",
                    "resolved_by": None,
                    "resolved_at": None,
                    "reason": "Custom gate",
                },
                "evidence": [
                    {
                        "kind": "log",
                        "label": "Custom gate log",
                        "ref": "log://triage-inbox/custom-pending",
                    }
                ],
                "meta": {"workflow": "triage_inbox", "step": "custom_gate"},
            },
        )
        assert ingest_response.status_code == 201

        approve_response = client.post(
            "/v1/approvals/evt_triage_inbox_custom_pending",
            json={
                "decision": "approved",
                "approver_id": "human_reviewer",
                "reason": "Approved custom event",
            },
        )
        assert approve_response.status_code == 200
        body = approve_response.json()
        assert body["run_status"] == "approved"
        assert body["orchestration"] == {"applied": False, "event_ids": []}

        events_response = client.get("/v1/runs/run_triage_inbox_demo_1/events")
        assert events_response.status_code == 200
        assert events_response.json()["event_count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_issue53_round1_approval_resolution_reports_mvp_timing_receipt() -> None:
    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    body = approve_response.json()
    assert body["timing"]["target_ms"] == 1000
    assert isinstance(body["timing"]["approval_to_state_update_ms"], int)
    assert body["timing"]["approval_to_state_update_ms"] >= 0
    assert isinstance(body["timing"]["within_target"], bool)
    assert body["timing"]["within_target"] == (
        body["timing"]["approval_to_state_update_ms"] <= body["timing"]["target_ms"]
    )


def test_issue53_round2_triage_inbox_reports_deterministic_orchestration_gap() -> None:
    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    body = approve_response.json()
    assert body["timing"]["orchestration_receipt_gap_ms"] == 2
    assert body["timing"]["orchestration_receipt_gap_ms"] <= body["timing"]["target_ms"]


def test_issue53_round3_timing_receipt_reports_state_transition() -> None:
    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    body = approve_response.json()
    assert body["timing"]["state_transition"] == "paused->completed"


def test_issue53_round6_timing_rounds_up_before_target_comparison(monkeypatch) -> None:
    from nightledger_api.services import approval_service

    timer_ticks = iter([100.0, 101.0001])
    monkeypatch.setattr(approval_service, "perf_counter", lambda: next(timer_ticks))

    reset_response = client.post("/v1/demo/triage_inbox/reset-seed")
    assert reset_response.status_code == 200

    approve_response = client.post(
        "/v1/approvals/evt_triage_inbox_003",
        json={
            "decision": "approved",
            "approver_id": "human_reviewer",
            "reason": "Approved for demo completion",
        },
    )
    assert approve_response.status_code == 200

    timing = approve_response.json()["timing"]
    assert timing["approval_to_state_update_ms"] == 1001
    assert timing["within_target"] is False
