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
    context_schema = tool["inputSchema"]["properties"]["context"]
    assert "user_id" in context_schema["properties"]
    assert "amount" in context_schema["properties"]
    assert "currency" in context_schema["properties"]
    assert "user_id" in context_schema["required"]


def test_mcp_tools_call_returns_allow_when_no_rule_matches() -> None:
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
                    "context": {
                        "user_id": "user_test",
                        "request_id": "req_1",
                        "amount": 100,
                        "currency": "EUR",
                    },
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result.get("isError") is not True
    decision = result["structuredContent"]
    assert decision["state"] == "allow"
    assert decision["reason_code"] == "POLICY_ALLOW_NO_MATCH"
    assert decision["decision_id"].startswith("dec_")


def test_mcp_tools_call_returns_requires_approval_when_rule_matches() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "purchase.create"},
                    "context": {
                        "user_id": "user_test",
                        "request_id": "req_2",
                        "amount": 101,
                        "currency": "EUR",
                    },
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result.get("isError") is not True
    decision = result["structuredContent"]
    assert decision["state"] == "requires_approval"
    assert decision["reason_code"] == "RULE_REQUIRE_APPROVAL"
    assert "execution_token" not in decision


def test_mcp_tools_call_returns_structured_validation_error_for_missing_amount() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "purchase.create"},
                    "context": {"user_id": "user_test", "request_id": "req_missing", "currency": "EUR"},
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
    assert detail_codes["context.amount"] == "MISSING_AMOUNT"


def test_mcp_tools_call_accepts_dynamic_action_string() -> None:
    server = MCPServer()

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "invoice.pay"},
                    "context": {"user_id": "user_test", "request_id": "req_dyn", "amount": 120, "currency": "EUR"},
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["structuredContent"]["state"] == "requires_approval"


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
                "context": {
                    "user_id": "user_test",
                    "request_id": "req_stream",
                    "amount": 100,
                    "currency": "EUR",
                },
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


def test_mcp_server_module_is_callable_over_stdio_transport(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"
    )

    rules_path = tmp_path / "stdio_rules.yaml"
    rules_path.write_text(
        (
            "users:\n"
            "  user_test:\n"
            "    rules:\n"
            "      - id: threshold\n"
            "        type: guardrail\n"
            "        applies_to: [\"purchase.create\"]\n"
            "        when: \"context.amount > 100\"\n"
            "        action: \"require_approval\"\n"
            "        reason: \"Above threshold\"\n"
        ),
        encoding="utf-8",
    )
    env["NIGHTLEDGER_USER_RULES_FILE"] = str(rules_path)

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
                "context": {
                    "user_id": "user_test",
                    "request_id": "req_stdio_module",
                    "amount": 120,
                    "currency": "EUR",
                },
            },
        },
    }
    payload = _encode_framed_message(initialize_request) + _encode_framed_message(call_request)

    process = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "nightledger_api.mcp_server"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=root,
        env=env,
        check=True,
    )

    output_stream = BytesIO(process.stdout)
    responses = _extract_framed_messages(output_stream)
    assert len(responses) == 2
    assert responses[0]["id"] == 11
    assert responses[1]["id"] == 12
    assert responses[1]["result"]["structuredContent"]["state"] == "requires_approval"
