import json
import sys
from typing import Any, BinaryIO

from pydantic import ValidationError

from nightledger_api.presenters.error_presenter import (
    present_authorize_action_validation_errors,
)
from nightledger_api.services.authorize_action_service import (
    AuthorizeActionRequest,
    evaluate_authorize_action,
)


_MCP_PROTOCOL_VERSION = "2025-06-18"
_SERVER_NAME = "nightledger"
_SERVER_VERSION = "0.1.0"


class MCPServer:
    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        message_id = message.get("id")

        if message.get("jsonrpc") != "2.0":
            return _error_response(message_id, code=-32600, message="Invalid Request")

        method = message.get("method")
        params = message.get("params", {})

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return _success_response(
                message_id,
                {
                    "protocolVersion": _MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": _SERVER_NAME,
                        "version": _SERVER_VERSION,
                    },
                },
            )
        if method == "tools/list":
            return _success_response(message_id, {"tools": [_authorize_action_tool_definition()]})
        if method == "tools/call":
            return self._handle_tools_call(message_id=message_id, params=params)

        if message_id is None:
            return None
        return _error_response(message_id, code=-32601, message="Method not found")

    def _handle_tools_call(
        self,
        *,
        message_id: Any,
        params: Any,
    ) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error_response(message_id, code=-32602, message="Invalid params")

        tool_name = params.get("name")
        if tool_name != "authorize_action":
            return _error_response(message_id, code=-32601, message="Tool not found")

        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return _error_response(message_id, code=-32602, message="Invalid params")

        try:
            payload = AuthorizeActionRequest.model_validate(arguments)
        except ValidationError as exc:
            envelope = present_authorize_action_validation_errors(exc.errors())
            return _success_response(
                message_id,
                {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                        }
                    ],
                    "structuredContent": envelope,
                },
            )

        decision = evaluate_authorize_action(payload=payload)
        return _success_response(
            message_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(decision, sort_keys=True, separators=(",", ":")),
                    }
                ],
                "structuredContent": decision,
            },
        )


def serve_streams(*, input_stream: BinaryIO, output_stream: BinaryIO) -> None:
    server = MCPServer()
    while True:
        try:
            message = _read_framed_message(input_stream)
        except json.JSONDecodeError:
            _write_framed_message(
                output_stream,
                _error_response(None, code=-32700, message="Parse error"),
            )
            continue
        except ValueError:
            _write_framed_message(
                output_stream,
                _error_response(None, code=-32600, message="Invalid Request"),
            )
            continue

        if message is None:
            return

        response = server.handle_message(message)
        if response is not None:
            _write_framed_message(output_stream, response)


def _authorize_action_tool_definition() -> dict[str, Any]:
    return {
        "name": "authorize_action",
        "description": (
            "Authorize an action intent before execution. "
            "Supports purchase.create in v1."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["intent", "context"],
            "properties": {
                "intent": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["purchase.create"]}
                    },
                },
                "context": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "transport_decision_hint": {
                            "type": "string",
                            "enum": ["allow", "requires_approval", "deny"],
                        }
                    },
                },
            },
        },
    }


def _success_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": result,
    }


def _error_response(message_id: Any, *, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _read_framed_message(input_stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = input_stream.readline()
        if line == b"":
            if not headers:
                return None
            raise ValueError("unexpected EOF while reading headers")
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    content_length = headers.get("content-length")
    if content_length is None:
        raise ValueError("missing content-length header")

    expected_bytes = int(content_length)
    payload = input_stream.read(expected_bytes)
    if len(payload) != expected_bytes:
        raise ValueError("incomplete message body")
    decoded_payload = payload.decode("utf-8")
    parsed = json.loads(decoded_payload)
    if not isinstance(parsed, dict):
        raise ValueError("request must be a JSON object")
    return parsed


def _write_framed_message(output_stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    output_stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    output_stream.write(body)
    output_stream.flush()


def main() -> None:
    serve_streams(input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)


if __name__ == "__main__":
    main()
