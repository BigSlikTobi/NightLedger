from io import BytesIO
import os
from pathlib import Path
import json
import subprocess
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.mcp_server import MCPServer, serve_streams  # noqa: E402


def _extract_framed_messages(buffer: BytesIO) -> list[dict[str, object]]:
    payload = buffer.getvalue()
    messages: list[dict[str, object]] = []
    offset = 0
    while offset < len(payload):
        header_end = payload.find(b"\r\n\r\n", offset)
        assert header_end != -1
        headers = payload[offset:header_end].decode("utf-8")
        content_length = None
        for line in headers.split("\r\n"):
            key, value = line.split(":", 1)
            if key.lower().strip() == "content-length":
                content_length = int(value.strip())
        assert content_length is not None
        body_start = header_end + 4
        body_end = body_start + content_length
        body = payload[body_start:body_end].decode("utf-8")
        messages.append(json.loads(body))
        offset = body_end
    return messages


def _encode_framed_message(message: dict[str, object]) -> bytes:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body


def test_mcp_initialize_returns_server_capabilities() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
    )

    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    result = response["result"]
    assert result["protocolVersion"]
    assert result["serverInfo"]["name"] == "nightledger"
    assert result["serverInfo"]["version"]
    assert "tools" in result["capabilities"]


def test_mcp_tools_list_exposes_authorize_action_contract() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )

    assert response is not None
    result = response["result"]
    assert "tools" in result
    tool = result["tools"][0]
    assert tool["name"] == "authorize_action"
    assert tool["inputSchema"]["type"] == "object"


def test_mcp_tools_call_returns_structured_authorize_action_decision() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "purchase.create"},
                    "context": {"request_id": "req_1", "transport_decision_hint": "deny"},
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result.get("isError") is not True
    decision = result["structuredContent"]
    assert decision["state"] == "deny"
    assert decision["reason_code"] == "TRANSPORT_DENIED"
    assert decision["decision_id"].startswith("dec_")


def test_mcp_tools_call_returns_structured_validation_error_for_invalid_action() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "transfer.create"},
                    "context": {"request_id": "req_bad"},
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    error_payload = result["structuredContent"]
    assert error_payload["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    detail_codes = {
        detail["path"]: detail["code"] for detail in error_payload["error"]["details"]
    }
    assert detail_codes["intent.action"] == "UNSUPPORTED_ACTION"


def test_mcp_ignores_initialized_notification() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
    )

    assert response is None


def test_mcp_serve_streams_processes_framed_jsonrpc_messages() -> None:
    input_stream = BytesIO()
    output_stream = BytesIO()
    request = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "authorize_action",
            "arguments": {
                "intent": {"action": "purchase.create"},
                "context": {"request_id": "req_stream", "transport_decision_hint": "allow"},
            },
        },
    }
    body = json.dumps(request, separators=(",", ":")).encode("utf-8")
    input_stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    input_stream.write(body)
    input_stream.seek(0)

    serve_streams(input_stream=input_stream, output_stream=output_stream)

    responses = _extract_framed_messages(output_stream)
    assert len(responses) == 1
    response = responses[0]
    assert response["id"] == 7
    assert response["result"]["structuredContent"]["state"] == "allow"


def test_mcp_server_module_is_callable_over_stdio_transport() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )

    initialize_request = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
    }
    call_request = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "authorize_action",
            "arguments": {
                "intent": {"action": "purchase.create"},
                "context": {"request_id": "req_proc", "transport_decision_hint": "requires_approval"},
            },
        },
    }
    payload = _encode_framed_message(initialize_request) + _encode_framed_message(call_request)

    proc = subprocess.Popen(
        [sys.executable, "-m", "nightledger_api.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout, stderr = proc.communicate(input=payload, timeout=5)
    assert proc.returncode == 0, stderr.decode("utf-8")

    output_buffer = BytesIO(stdout)
    responses = _extract_framed_messages(output_buffer)
    assert len(responses) == 2
    assert responses[0]["id"] == 11
    assert responses[0]["result"]["serverInfo"]["name"] == "nightledger"
    assert responses[1]["id"] == 12
    assert (
        responses[1]["result"]["structuredContent"]["state"]
        == "requires_approval"
    )
