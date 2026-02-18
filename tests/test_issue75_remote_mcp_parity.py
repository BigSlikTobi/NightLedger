from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app as api_app  # noqa: E402
from nightledger_api.mcp_protocol import MCPServer  # noqa: E402
from nightledger_api.mcp_remote_server import app as remote_app  # noqa: E402


api_client = TestClient(api_app)
remote_client = TestClient(remote_app)


def test_issue75_authorize_action_decision_is_identical_across_http_stdio_and_remote(
    monkeypatch,
) -> None:
    payload = {
        "intent": {"action": "purchase.create"},
        "context": {
            "request_id": "req_issue75_parity",
            "amount": 101,
            "currency": "EUR",
            "transport_decision_hint": "allow",
        },
    }

    http_response = api_client.post("/v1/mcp/authorize_action", json=payload)
    assert http_response.status_code == 200
    http_decision = http_response.json()

    stdio_response = MCPServer().handle_message(
        {
            "jsonrpc": "2.0",
            "id": 75,
            "method": "tools/call",
            "params": {"name": "authorize_action", "arguments": payload},
        }
    )
    assert stdio_response is not None
    stdio_decision = stdio_response["result"]["structuredContent"]

    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "issue75-secret")
    initialize_response = remote_client.post(
        "/v1/mcp/remote",
        headers={
            "Authorization": "Bearer issue75-secret",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 760,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "parity-client", "version": "0.1.0"},
            },
        },
    )
    assert initialize_response.status_code == 200
    session_id = initialize_response.headers.get("MCP-Session-Id")
    assert session_id

    remote_response = remote_client.post(
        "/v1/mcp/remote",
        headers={
            "Authorization": "Bearer issue75-secret",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "MCP-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={
            "jsonrpc": "2.0",
            "id": 76,
            "method": "tools/call",
            "params": {"name": "authorize_action", "arguments": payload},
        },
    )
    assert remote_response.status_code == 200
    remote_decision = remote_response.json()["result"]["structuredContent"]

    assert http_decision["decision_id"] == stdio_decision["decision_id"]
    assert http_decision["decision_id"] == remote_decision["decision_id"]
    assert http_decision["state"] == "requires_approval"
    assert http_decision["state"] == stdio_decision["state"] == remote_decision["state"]
    assert (
        http_decision["reason_code"]
        == stdio_decision["reason_code"]
        == remote_decision["reason_code"]
    )
