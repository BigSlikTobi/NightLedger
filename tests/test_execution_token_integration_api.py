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


def _authorize_payload(amount: int) -> dict[str, object]:
    return {
        "intent": {"action": "purchase.create"},
        "context": {
            "request_id": f"req_{amount}",
            "amount": amount,
            "currency": "EUR",
        },
    }



def _exec_payload() -> dict[str, object]:
    return {
        "amount": 100,
        "currency": "EUR",
        "merchant": "ACME GmbH",
    }



def test_authorize_action_allow_returns_execution_token(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round4-secret")

    response = client.post("/v1/mcp/authorize_action", json=_authorize_payload(100))

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "allow"
    assert body["execution_token"]
    assert body["execution_token_expires_at"]



def test_authorize_action_requires_approval_has_no_execution_token() -> None:
    response = client.post("/v1/mcp/authorize_action", json=_authorize_payload(101))

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "requires_approval"
    assert "execution_token" not in body



def test_mint_execution_token_by_decision_id_requires_approved_state() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    register = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_round4_pending",
            "run_id": "run_round4_pending",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register.status_code == 200

    response = client.post("/v1/approvals/decisions/dec_round4_pending/execution-token")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EXECUTION_DECISION_NOT_APPROVED"



def test_mint_execution_token_by_decision_id_succeeds_when_approved(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round4-secret")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    register = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": "dec_round4_approved",
            "run_id": "run_round4_approved",
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register.status_code == 200

    resolve = client.post(
        "/v1/approvals/decisions/dec_round4_approved",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert resolve.status_code == 200

    response = client.post("/v1/approvals/decisions/dec_round4_approved/execution-token")

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] == "dec_round4_approved"
    assert body["action"] == "purchase.create"
    assert body["execution_token"]
    assert body["expires_at"]



def test_purchase_executor_rejects_replayed_token(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round4-secret")

    authorize = client.post("/v1/mcp/authorize_action", json=_authorize_payload(100))
    assert authorize.status_code == 200
    token = authorize.json()["execution_token"]

    first = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert second.status_code == 403
    body = second.json()
    assert body["error"]["code"] == "EXECUTION_TOKEN_REPLAYED"
