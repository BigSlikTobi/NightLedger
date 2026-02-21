from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()



def _authorize_payload(amount: int, request_id: str) -> dict[str, object]:
    return {
        "intent": {"action": "purchase.create"},
        "context": {
            "user_id": "user_test",
            "request_id": request_id,
            "amount": amount,
            "currency": "EUR",
            "merchant": "ACME GmbH",
        },
    }



def _exec_payload(amount: int = 100) -> dict[str, object]:
    return {
        "amount": amount,
        "currency": "EUR",
        "merchant": "ACME GmbH",
    }



def test_issue47_allow_path_executes_then_replay_is_blocked(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-secret-key-material-32bytes!!")

    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(100, "req_issue47_allow"),
    )
    assert authorize.status_code == 200
    body = authorize.json()
    assert body["state"] == "allow"
    token = body["execution_token"]

    first = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    replay = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert replay.status_code == 403
    assert replay.json()["error"]["code"] == "EXECUTION_TOKEN_REPLAYED"



def test_issue47_requires_approval_path_blocks_then_allows_post_approval(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-secret-key-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(500, "req_issue47_blocked"),
    )
    assert authorize.status_code == 200
    decision = authorize.json()
    assert decision["state"] == "requires_approval"
    decision_id = decision["decision_id"]

    blocked = client.post("/v1/executors/purchase.create", json=_exec_payload(amount=500))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "EXECUTION_TOKEN_MISSING"

    register = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": decision_id,
            "run_id": "run_issue47_path",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register.status_code == 200

    pending_mint = client.post(
        f"/v1/approvals/decisions/{decision_id}/execution-token",
        json={"amount": 500, "currency": "EUR", "merchant": "ACME GmbH"},
    )
    assert pending_mint.status_code == 409
    assert pending_mint.json()["error"]["code"] == "EXECUTION_DECISION_NOT_APPROVED"

    resolve = client.post(
        f"/v1/approvals/decisions/{decision_id}",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert resolve.status_code == 200

    mint = client.post(
        f"/v1/approvals/decisions/{decision_id}/execution-token",
        json={"amount": 500, "currency": "EUR", "merchant": "ACME GmbH"},
    )
    assert mint.status_code == 200
    token = mint.json()["execution_token"]

    execute = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(amount=500),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert execute.status_code == 200
    assert execute.json()["decision_id"] == decision_id


def test_issue47_requires_explicit_registration_before_decision_state_exists() -> None:
    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(500, "req_issue47_registration_required"),
    )
    assert authorize.status_code == 200
    decision_id = authorize.json()["decision_id"]

    unresolved = client.get(f"/v1/approvals/decisions/{decision_id}")
    assert unresolved.status_code == 404
    assert unresolved.json()["error"]["code"] == "APPROVAL_NOT_FOUND"

    blocked_resolve = client.post(
        f"/v1/approvals/decisions/{decision_id}",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert blocked_resolve.status_code == 409
    assert blocked_resolve.json()["error"]["code"] == "NO_PENDING_APPROVAL"


def test_issue47_decision_polling_drives_resume_for_approved_and_rejected() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    approve_authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(500, "req_issue47_poll_approved"),
    )
    approve_decision_id = approve_authorize.json()["decision_id"]
    register_approved = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": approve_decision_id,
            "run_id": "run_issue47_poll_approved",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_approved.status_code == 200

    pending_state = client.get(f"/v1/approvals/decisions/{approve_decision_id}")
    assert pending_state.status_code == 200
    assert pending_state.json()["status"] == "pending"

    approve = client.post(
        f"/v1/approvals/decisions/{approve_decision_id}",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert approve.status_code == 200

    approved_state = client.get(f"/v1/approvals/decisions/{approve_decision_id}")
    assert approved_state.status_code == 200
    assert approved_state.json()["status"] == "approved"

    approved_mint = client.post(
        f"/v1/approvals/decisions/{approve_decision_id}/execution-token",
        json={"amount": 500, "currency": "EUR", "merchant": "ACME GmbH"},
    )
    assert approved_mint.status_code == 200

    reject_authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(500, "req_issue47_poll_rejected"),
    )
    reject_decision_id = reject_authorize.json()["decision_id"]
    register_rejected = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": reject_decision_id,
            "run_id": "run_issue47_poll_rejected",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register_rejected.status_code == 200

    reject = client.post(
        f"/v1/approvals/decisions/{reject_decision_id}",
        json={"decision": "rejected", "approver_id": "human_reviewer"},
    )
    assert reject.status_code == 200

    rejected_state = client.get(f"/v1/approvals/decisions/{reject_decision_id}")
    assert rejected_state.status_code == 200
    assert rejected_state.json()["status"] == "rejected"

    rejected_mint = client.post(
        f"/v1/approvals/decisions/{reject_decision_id}/execution-token",
        json={"amount": 500, "currency": "EUR", "merchant": "ACME GmbH"},
    )
    assert rejected_mint.status_code == 409
    assert rejected_mint.json()["error"]["code"] == "EXECUTION_DECISION_NOT_APPROVED"
