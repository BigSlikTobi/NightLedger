from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.mcp_remote_server import app  # noqa: E402


client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer test-remote-token",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _initialize_session(monkeypatch) -> str:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    response = client.post(
        "/v1/mcp/remote",
        headers=_auth_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "remote-test", "version": "0.1.0"},
            },
        },
    )
    assert response.status_code == 200
    session_id = response.headers.get("MCP-Session-Id")
    assert session_id
    return session_id


def _session_headers(*, session_id: str) -> dict[str, str]:
    return {
        **_auth_headers(),
        "MCP-Session-Id": session_id,
        "MCP-Protocol-Version": "2025-06-18",
    }


def test_remote_mcp_initialize_over_http_returns_session_id(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    assert session_id

    response = client.post(
        "/v1/mcp/remote",
        headers=_session_headers(session_id=session_id),
        json={"jsonrpc": "2.0", "id": 11, "method": "tools/list", "params": {}},
    )
    body = response.json()
    assert body["id"] == 11
    assert body["result"]["tools"][0]["name"] == "authorize_action"


def test_remote_mcp_tools_list_over_http(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    response = client.post(
        "/v1/mcp/remote",
        headers=_session_headers(session_id=session_id),
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 2
    assert body["result"]["tools"][0]["name"] == "authorize_action"


def test_remote_mcp_tools_call_over_http_returns_deterministic_decision(
    monkeypatch,
) -> None:
    session_id = _initialize_session(monkeypatch)
    response = client.post(
        "/v1/mcp/remote",
        headers=_session_headers(session_id=session_id),
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "purchase.create"},
                    "context": {"request_id": "req_remote", "amount": 101, "currency": "EUR"},
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 3
    assert body["result"]["structuredContent"]["state"] == "requires_approval"
    assert body["result"]["structuredContent"]["reason_code"] == "AMOUNT_ABOVE_THRESHOLD"
    assert "execution_token" not in body["result"]["structuredContent"]


def test_remote_mcp_rejects_missing_session_on_non_initialize(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    response = client.post(
        "/v1/mcp/remote",
        headers=_auth_headers(),
        json={"jsonrpc": "2.0", "id": 20, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32003


def test_remote_mcp_rejects_unknown_session_id(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    response = client.post(
        "/v1/mcp/remote",
        headers=_session_headers(session_id="unknown-session-id"),
        json={"jsonrpc": "2.0", "id": 21, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == -32004


def test_remote_mcp_rejects_missing_protocol_header_for_session_requests(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    headers = _auth_headers()
    headers["MCP-Session-Id"] = session_id
    response = client.post(
        "/v1/mcp/remote",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 22, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32005


def test_remote_mcp_rejects_invalid_origin(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS", "https://trusted.example")
    response = client.post(
        "/v1/mcp/remote",
        headers={
            **_auth_headers(),
            "Origin": "https://evil.example",
        },
        json={"jsonrpc": "2.0", "id": 23, "method": "initialize", "params": {}},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == -32006


def test_remote_mcp_allows_listed_origin(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS", "https://trusted.example")
    response = client.post(
        "/v1/mcp/remote",
        headers={
            **_auth_headers(),
            "Origin": "https://trusted.example",
        },
        json={"jsonrpc": "2.0", "id": 24, "method": "initialize", "params": {}},
    )
    assert response.status_code == 200
    assert response.headers.get("MCP-Session-Id")


def test_remote_mcp_get_sse_stream_returns_event_stream(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    response = client.get(
        "/v1/mcp/remote",
        headers={
            "Authorization": "Bearer test-remote-token",
            "Accept": "text/event-stream",
            "MCP-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-06-18",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in response.text


def test_remote_mcp_post_can_stream_sse_when_requested(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    response = client.post(
        "/v1/mcp/remote",
        headers={
            **_session_headers(session_id=session_id),
            "Accept": "text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": 25, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"jsonrpc":"2.0"' in response.text


def test_remote_mcp_delete_terminates_session(monkeypatch) -> None:
    session_id = _initialize_session(monkeypatch)
    delete_response = client.delete(
        "/v1/mcp/remote",
        headers={
            "Authorization": "Bearer test-remote-token",
            "MCP-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-06-18",
        },
    )
    assert delete_response.status_code == 204

    response = client.post(
        "/v1/mcp/remote",
        headers=_session_headers(session_id=session_id),
        json={"jsonrpc": "2.0", "id": 26, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == -32004


def test_remote_mcp_oauth_protected_resource_metadata(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTHORIZATION_SERVERS", "https://auth.example")
    response = client.get("/.well-known/oauth-protected-resource")
    assert response.status_code == 200
    body = response.json()
    assert "authorization_servers" in body
    assert body["authorization_servers"] == ["https://auth.example"]


def test_remote_mcp_rejects_missing_auth_with_structured_error(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    response = client.post(
        "/v1/mcp/remote",
        headers={"Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 4, "method": "initialize", "params": {}},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == -32001
    assert body["error"]["message"] == "Unauthorized"
    assert body["error"]["data"]["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"].startswith("Bearer ")


def test_remote_mcp_rejects_invalid_auth_token_with_structured_error(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", "test-remote-token")
    response = client.post(
        "/v1/mcp/remote",
        headers={"Authorization": "Bearer wrong-token", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == -32001
    assert body["error"]["data"]["error"]["code"] == "UNAUTHORIZED"


def test_remote_mcp_rejects_when_auth_token_is_misconfigured(monkeypatch) -> None:
    monkeypatch.delenv("NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN", raising=False)
    response = client.post(
        "/v1/mcp/remote",
        headers={"Authorization": "Bearer any", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 6, "method": "initialize", "params": {}},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == -32002
    assert body["error"]["message"] == "Remote auth misconfigured"
    assert body["error"]["data"]["error"]["code"] == "REMOTE_AUTH_MISCONFIGURED"
