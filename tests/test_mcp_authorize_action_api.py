from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402


client = TestClient(app)


def _valid_payload() -> dict[str, object]:
    return {
        "intent": {"action": "purchase.create"},
        "context": {"request_id": "req_123", "amount": 42, "currency": "EUR"},
    }


def _extract_detail_codes(body: dict[str, object]) -> dict[str, str]:
    details = body["error"]["details"]
    return {detail["path"]: detail["code"] for detail in details}


def test_authorize_action_returns_allow_and_deterministic_decision_id() -> None:
    payload = _valid_payload()

    first = client.post("/v1/mcp/authorize_action", json=payload)
    second = client.post("/v1/mcp/authorize_action", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["state"] == "allow"
    assert first_body["reason_code"] == "TRANSPORT_CONTRACT_ACCEPTED"
    assert first_body["decision_id"] == second_body["decision_id"]
    assert first_body["decision_id"].startswith("dec_")


def test_authorize_action_rejects_unsupported_action_with_structured_error() -> None:
    payload = _valid_payload()
    payload["intent"] = {"action": "transfer.create"}

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["intent.action"] == "UNSUPPORTED_ACTION"


def test_authorize_action_rejects_missing_intent_and_context_with_structured_errors() -> None:
    response = client.post("/v1/mcp/authorize_action", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["intent"] == "MISSING_INTENT"
    assert detail_codes["context"] == "MISSING_CONTEXT"
