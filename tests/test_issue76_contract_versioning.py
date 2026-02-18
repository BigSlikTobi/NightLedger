from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402
from nightledger_api.mcp_protocol import authorize_action_tool_definition  # noqa: E402
from nightledger_api.services.authorize_action_service import (  # noqa: E402
    AUTHORIZE_ACTION_CONTRACT_VERSION,
)


client = TestClient(app)


def test_issue76_authorize_action_http_response_includes_contract_version() -> None:
    response = client.post(
        "/v1/mcp/authorize_action",
        json={
            "intent": {"action": "purchase.create"},
            "context": {
                "request_id": "req_issue76_contract",
                "amount": 100,
                "currency": "EUR",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == AUTHORIZE_ACTION_CONTRACT_VERSION


def test_issue76_mcp_tool_definition_includes_contract_version_metadata() -> None:
    tool = authorize_action_tool_definition()
    metadata = tool["x-nightledger-contract"]
    assert metadata["name"] == "authorize_action"
    assert metadata["version"] == AUTHORIZE_ACTION_CONTRACT_VERSION
    assert metadata["compatibility"] == "backward-compatible"
