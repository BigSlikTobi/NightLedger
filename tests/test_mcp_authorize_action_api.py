from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402


client = TestClient(app)


def _valid_payload(
    *,
    user_id: str = "user_test",
    action: str = "purchase.create",
    amount: int | float = 100,
    currency: str = "EUR",
    merchant: str = "ACME GmbH",
) -> dict[str, object]:
    return {
        "intent": {"action": action},
        "context": {
            "request_id": "req_123",
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "merchant": merchant,
        },
    }


def _extract_detail_codes(body: dict[str, object]) -> dict[str, str]:
    details = body["error"]["details"]
    return {detail["path"]: detail["code"] for detail in details}


def test_authorize_action_returns_allow_for_no_rule_match_and_deterministic_decision_id() -> None:
    payload = _valid_payload(amount=100)

    first = client.post("/v1/mcp/authorize_action", json=payload)
    second = client.post("/v1/mcp/authorize_action", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["state"] == "allow"
    assert first_body["reason_code"] == "POLICY_ALLOW_NO_MATCH"
    assert first_body["decision_id"] == second_body["decision_id"]
    assert first_body["decision_id"].startswith("dec_")


def test_authorize_action_returns_requires_approval_when_threshold_rule_matches() -> None:
    response = client.post("/v1/mcp/authorize_action", json=_valid_payload(amount=101))

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "requires_approval"
    assert body["reason_code"] == "RULE_REQUIRE_APPROVAL"
    assert body["matched_rule_ids"] == ["amount_threshold"]


def test_authorize_action_returns_deny_when_blocked_merchant_matches(monkeypatch, tmp_path) -> None:
    rules_file = tmp_path / "deny_rules.yaml"
    rules_file.write_text(
        (
            "users:\n"
            "  user_test:\n"
            "    rules:\n"
            "      - id: blocked_merchant\n"
            "        type: guardrail\n"
            "        applies_to: [\"purchase.create\"]\n"
            "        when: \"context.merchant in ['Bad Shop GmbH']\"\n"
            "        action: \"deny\"\n"
            "        reason: \"Merchant is blocked\"\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NIGHTLEDGER_USER_RULES_FILE", str(rules_file))

    response = client.post(
        "/v1/mcp/authorize_action",
        json=_valid_payload(amount=50, merchant="Bad Shop GmbH"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "deny"
    assert body["reason_code"] == "RULE_DENY"
    assert "blocked_merchant" in body["matched_rule_ids"]


def test_authorize_action_accepts_non_purchase_action() -> None:
    response = client.post(
        "/v1/mcp/authorize_action",
        json=_valid_payload(action="invoice.pay", amount=120),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "requires_approval"
    assert body["reason_code"] == "RULE_REQUIRE_APPROVAL"


def test_authorize_action_returns_allow_for_unconfigured_user() -> None:
    response = client.post(
        "/v1/mcp/authorize_action",
        json=_valid_payload(user_id="user_unknown", amount=9999),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "allow"
    assert body["reason_code"] == "POLICY_ALLOW_NO_MATCH"
    assert body["matched_rule_ids"] == []


def test_authorize_action_rejects_missing_user_id_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"].pop("user_id")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.user_id"] == "MISSING_USER_ID"


def test_authorize_action_rejects_missing_amount_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"].pop("amount")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.amount"] == "MISSING_AMOUNT"


def test_authorize_action_rejects_invalid_amount_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"]["amount"] = "not-a-number"

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.amount"] == "INVALID_AMOUNT"


def test_authorize_action_rejects_missing_currency_with_structured_error() -> None:
    payload = _valid_payload()
    payload["context"].pop("currency")

    response = client.post("/v1/mcp/authorize_action", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.currency"] == "MISSING_CURRENCY"


def test_authorize_action_rejects_unsupported_currency_with_structured_error() -> None:
    response = client.post("/v1/mcp/authorize_action", json=_valid_payload(currency="USD"))

    assert response.status_code == 422
    body = response.json()
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["context.currency"] == "UNSUPPORTED_CURRENCY"


def test_authorize_action_rejects_missing_intent_and_context_with_structured_errors() -> None:
    response = client.post("/v1/mcp/authorize_action", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = _extract_detail_codes(body)
    assert detail_codes["intent"] == "MISSING_INTENT"
    assert detail_codes["context"] == "MISSING_CONTEXT"


def test_authorize_action_fails_loud_with_rule_configuration_error(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_USER_RULES_FILE", "/tmp/does-not-exist-nightledger.yaml")
    response = client.post("/v1/mcp/authorize_action", json=_valid_payload())

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "RULE_CONFIGURATION_ERROR"


def test_authorize_action_rejects_missing_rule_input(monkeypatch, tmp_path) -> None:
    rules_file = tmp_path / "missing_input_rules.yaml"
    rules_file.write_text(
        (
            "users:\n"
            "  user_test:\n"
            "    rules:\n"
            "      - id: budget_monthly_cap\n"
            "        type: guardrail\n"
            "        applies_to: [\"purchase.create\"]\n"
            "        when: \"context.projected_monthly_spend > 50000\"\n"
            "        action: \"require_approval\"\n"
            "        reason: \"Monthly budget cap exceeded\"\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NIGHTLEDGER_USER_RULES_FILE", str(rules_file))

    response = client.post("/v1/mcp/authorize_action", json=_valid_payload())
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["error"]["details"][0]["code"] == "MISSING_RULE_INPUT"
    assert body["error"]["details"][0]["path"] == "context.projected_monthly_spend"


def test_authorize_action_fails_loud_with_invalid_rule_expression(monkeypatch, tmp_path) -> None:
    rules_file = tmp_path / "invalid_expr_rules.yaml"
    rules_file.write_text(
        (
            "users:\n"
            "  user_test:\n"
            "    rules:\n"
            "      - id: broken_rule\n"
            "        type: guardrail\n"
            "        applies_to: [\"purchase.create\"]\n"
            "        when: \"context.amount >\"\n"
            "        action: \"require_approval\"\n"
            "        reason: \"Broken\"\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NIGHTLEDGER_USER_RULES_FILE", str(rules_file))

    response = client.post("/v1/mcp/authorize_action", json=_valid_payload())
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "RULE_EXPRESSION_INVALID"
