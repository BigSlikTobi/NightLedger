from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.mcp_server import MCPServer as StdioMCPServer  # noqa: E402
from nightledger_api.mcp_protocol import MCPServer as SharedMCPServer  # noqa: E402


def test_stdio_server_uses_shared_mcp_server_implementation() -> None:
    assert StdioMCPServer is SharedMCPServer


def test_shared_mcp_server_tools_call_returns_structured_decision() -> None:
    server = SharedMCPServer()
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "authorize_action",
                "arguments": {
                    "intent": {"action": "purchase.create"},
                    "context": {
                        "user_id": "user_test",
                        "request_id": "req_shared",
                        "amount": 101,
                        "currency": "EUR",
                    },
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["structuredContent"]["state"] == "requires_approval"
    assert result["structuredContent"]["reason_code"] == "RULE_REQUIRE_APPROVAL"
