from datetime import datetime, timezone
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.execution_token_service import mint_execution_token  # noqa: E402


client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "amount": 100,
        "currency": "EUR",
        "merchant": "ACME GmbH",
    }


def test_purchase_executor_blocks_missing_token() -> None:
    response = client.post("/v1/executors/purchase.create", json=_payload())

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "EXECUTION_TOKEN_MISSING"


def test_purchase_executor_blocks_invalid_token() -> None:
    response = client.post(
        "/v1/executors/purchase.create",
        json=_payload(),
        headers={"Authorization": "Bearer not.a.valid.token"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "EXECUTION_TOKEN_INVALID"


def test_purchase_executor_blocks_expired_token(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round3-secret")
    token, _ = mint_execution_token(
        decision_id="dec_round3_expired",
        action="purchase.create",
        now=datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc),
        secret="round3-secret",
        ttl_seconds=1,
    )

    response = client.post(
        "/v1/executors/purchase.create",
        json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "EXECUTION_TOKEN_EXPIRED"


def test_purchase_executor_blocks_action_mismatch_token(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round3-secret")
    token, _ = mint_execution_token(
        decision_id="dec_round3_action_mismatch",
        action="transfer.create",
        now=datetime.now(timezone.utc),
        secret="round3-secret",
        ttl_seconds=300,
    )

    response = client.post(
        "/v1/executors/purchase.create",
        json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "EXECUTION_ACTION_MISMATCH"


def test_purchase_executor_allows_valid_token_and_returns_receipt(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "round3-secret")
    token, _ = mint_execution_token(
        decision_id="dec_round3_valid",
        action="purchase.create",
        now=datetime.now(timezone.utc),
        secret="round3-secret",
        ttl_seconds=300,
    )

    response = client.post(
        "/v1/executors/purchase.create",
        json=_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "executed"
    assert body["action"] == "purchase.create"
    assert body["decision_id"] == "dec_round3_valid"
    assert body["execution_id"].startswith("exec_")
