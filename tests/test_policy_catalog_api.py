from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402


client = TestClient(app)


def test_get_policy_catalog_returns_version_and_actions() -> None:
    response = client.get("/v1/policy/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["policy_set"] == "nightledger-v2-user-local"
    assert body["catalog_version"].startswith("pol_")
    assert "purchase.create" in body["protected_actions"]
    assert "invoice.pay" in body["protected_actions"]


def test_get_policy_catalog_can_filter_by_user() -> None:
    response = client.get("/v1/policy/catalog", params={"user_id": "user_test"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["users"]) == 1
    assert body["users"][0]["user_id"] == "user_test"


def test_authorize_action_rejects_stale_catalog_version() -> None:
    response = client.post(
        "/v1/mcp/authorize_action",
        json={
            "intent": {"action": "purchase.create"},
            "context": {
                "user_id": "user_test",
                "request_id": "req_policy_mismatch",
                "amount": 100,
                "currency": "EUR",
                "policy_catalog_version": "pol_stale",
            },
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "POLICY_CATALOG_VERSION_MISMATCH"
    assert body["error"]["details"][0]["path"] == "context.policy_catalog_version"
