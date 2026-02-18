from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402


client = TestClient(app)


def _valid_payload(
    *,
    amount: int | float = 100,
    currency: str = "EUR",
    transport_decision_hint: str | None = None,
) -> dict[str, object]:
    context: dict[str, object] = {
        "request_id": "req_123",
        "amount": amount,
        "currency": currency,
    }
    if transport_decision_hint is not None:
        context["transport_decision_hint"] = transport_decision_hint

    return {
        "intent": {"action": "purchase.create"},
        "context": context,
    }


def _extract_detail_codes(body: dict[str, object]) -> dict[str, str]:
    details = body["error"]["details"]
    return {detail["path"]: detail["code"] for detail in details}


def test_authorize_action_returns_allow_at_threshold_and_deterministic_decision_id() -> None:
    payload = _valid_payload(amount=100)

    first = client.post("/v1/mcp/authorize_action", json=payload)
    second = client.post("/v1/mcp/authorize_action", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["state"] == "allow"
    assert first_body["reason_code"] == "POLICY_ALLOW_WITHIN_THRESHOLD"
    assert first_body["decision_id"] == second_body["decision_id"]
    assert first_body["decision_id"].startswith("dec_")


def test_authorize_action_returns_requires_approval_above_threshold() -> None:
    response = client.post("/v1/mcp/authorize_action", json=_valid_payload(amount=101))

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "requires_approval"
    assert body["reason_code"] == "AMOUNT_ABOVE_THRESHOLD"


def test_authorize_action_uses_env_threshold_override(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR", "50")

    allow_response = client.post("/v1/mcp/authorize_action", json=_valid_payload(amount=50))
    pause_response = client.post("/v1/mcp/authorize_action", json=_valid_payload(amount=51))

    assert allow_response.status_code == 200
    assert pause_response.status_code == 200
    assert allow_response.json()["state"] == "allow"
    assert pause_response.json()["state"] == "requires_approval"


def test_authorize_action_ignores_transport_hint_when_policy_allows() -> None:
    payload = _valid_payload(amount=100, transport_decision_hint="deny")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "allow"
    assert body["reason_code"] == "POLICY_ALLOW_WITHIN_THRESHOLD"


def test_authorize_action_ignores_transport_hint_when_policy_requires_approval() -> None:
    payload = _valid_payload(amount=101, transport_decision_hint="allow")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "requires_approval"
    assert body["reason_code"] == "AMOUNT_ABOVE_THRESHOLD"


def test_authorize_action_rejects_unsupported_action_with_structured_error() -> None:
    payload = _valid_payload()
    payload["intent"] = {"action": "transfer.create"}

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["intent.action"] == "UNSUPPORTED_ACTION"


def test_authorize_action_rejects_missing_amount_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"] = {
        "request_id": "req_missing_amount",
        "currency": "EUR",
    }

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.amount"] == "MISSING_AMOUNT"


def test_authorize_action_rejects_invalid_amount_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"] = {
        "request_id": "req_bad_amount",
        "amount": "not-a-number",
        "currency": "EUR",
    }

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.amount"] == "INVALID_AMOUNT"


def test_authorize_action_rejects_missing_currency_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"] = {
        "request_id": "req_missing_currency",
        "amount": 20,
    }

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.currency"] == "MISSING_CURRENCY"


def test_authorize_action_rejects_unsupported_currency_with_structured_error() -> None:
    payload = _valid_payload(currency="USD")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.currency"] == "UNSUPPORTED_CURRENCY"


def test_authorize_action_rejects_invalid_decision_hint_with_structured_error() -> None:
    payload = _valid_payload(transport_decision_hint="maybe")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert (
        detail_codes["context.transport_decision_hint"]
        == "INVALID_TRANSPORT_DECISION_HINT"
    )


def test_authorize_action_rejects_missing_intent_and_context_with_structured_errors() -> None:
    response = client.post("/v1/mcp/authorize_action", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["intent"] == "MISSING_INTENT"
    assert detail_codes["context"] == "MISSING_CONTEXT"
