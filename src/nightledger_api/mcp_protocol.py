import json
from typing import Any

from pydantic import ValidationError

from nightledger_api.presenters.error_presenter import (
    present_authorize_action_validation_errors,
)
from nightledger_api.services.authorize_action_service import (
    AuthorizeActionRequest,
    evaluate_authorize_action,
)


MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_SERVER_NAME = "nightledger"
MCP_SERVER_VERSION = "0.1.0"


class MCPServer:
    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        message_id = message.get("id")

        if message.get("jsonrpc") != "2.0":
            return error_response(message_id, code=-32600, message="Invalid Request")

        method = message.get("method")
        params = message.get("params", {})

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return success_response(
                message_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": MCP_SERVER_NAME,
                        "version": MCP_SERVER_VERSION,
                    },
                },
            )
        if method == "tools/list":
            return success_response(message_id, {"tools": [authorize_action_tool_definition()]})
        if method == "tools/call":
            return self._handle_tools_call(message_id=message_id, params=params)

        if message_id is None:
            return None
        return error_response(message_id, code=-32601, message="Method not found")

    def _handle_tools_call(
        self,
        *,
        message_id: Any,
        params: Any,
    ) -> dict[str, Any]:
        if not isinstance(params, dict):
            return error_response(message_id, code=-32602, message="Invalid params")

        tool_name = params.get("name")
        if tool_name != "authorize_action":
            return error_response(message_id, code=-32601, message="Tool not found")

        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return error_response(message_id, code=-32602, message="Invalid params")

        try:
            payload = AuthorizeActionRequest.model_validate(arguments)
        except ValidationError as exc:
            envelope = present_authorize_action_validation_errors(exc.errors())
            return success_response(
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
        return success_response(
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


def authorize_action_tool_definition() -> dict[str, Any]:
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
                    "required": ["amount", "currency"],
                    "properties": {
                        "amount": {"type": "number"},
                        "currency": {"type": "string", "enum": ["EUR"]},
                        "transport_decision_hint": {
                            "type": "string",
                            "enum": ["allow", "requires_approval", "deny"],
                        }
                    },
                },
            },
        },
    }


def success_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": result,
    }


def error_response(message_id: Any, *, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }
