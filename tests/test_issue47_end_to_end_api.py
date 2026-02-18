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
            "request_id": request_id,
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



def test_issue47_allow_path_executes_then_replay_is_blocked(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-secret")

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
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-secret")
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

    blocked = client.post("/v1/executors/purchase.create", json=_exec_payload())
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

    pending_mint = client.post(f"/v1/approvals/decisions/{decision_id}/execution-token")
    assert pending_mint.status_code == 409
    assert pending_mint.json()["error"]["code"] == "EXECUTION_DECISION_NOT_APPROVED"

    resolve = client.post(
        f"/v1/approvals/decisions/{decision_id}",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert resolve.status_code == 200

    mint = client.post(f"/v1/approvals/decisions/{decision_id}/execution-token")
    assert mint.status_code == 200
    token = mint.json()["execution_token"]

    execute = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert execute.status_code == 200
    assert execute.json()["decision_id"] == decision_id
