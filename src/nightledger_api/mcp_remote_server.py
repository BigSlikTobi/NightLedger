import json
import os
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse

from nightledger_api.mcp_protocol import MCPServer, error_response


_REMOTE_AUTH_TOKEN_ENV = "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN"
_REMOTE_ALLOWED_ORIGINS_ENV = "NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS"
_REMOTE_AUTHORIZATION_SERVERS_ENV = "NIGHTLEDGER_MCP_REMOTE_AUTHORIZATION_SERVERS"
_REMOTE_UNAUTHORIZED_CODE = -32001
_REMOTE_MISCONFIGURED_CODE = -32002
_REMOTE_SESSION_REQUIRED_CODE = -32003
_REMOTE_SESSION_NOT_FOUND_CODE = -32004
_REMOTE_PROTOCOL_REQUIRED_CODE = -32005
_REMOTE_ORIGIN_FORBIDDEN_CODE = -32006
_MCP_SESSION_HEADER = "MCP-Session-Id"
_MCP_PROTOCOL_HEADER = "MCP-Protocol-Version"
_MCP_PROTOCOL_VERSION = "2025-06-18"

app = FastAPI(title="NightLedger MCP Remote Server", version="0.1.0")
_server = MCPServer()
_sessions: dict[str, str] = {}


def _configured_auth_token() -> str | None:
    configured = os.getenv(_REMOTE_AUTH_TOKEN_ENV)
    if configured is None:
        return None
    token = configured.strip()
    if token == "":
        return None
    return token


def _extract_supplied_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer:
            return bearer
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    return None


def _configured_allowed_origins() -> set[str]:
    configured = os.getenv(_REMOTE_ALLOWED_ORIGINS_ENV, "")
    allowed = {value.strip() for value in configured.split(",") if value.strip()}
    return allowed


def _origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin", "").strip()
    if origin == "":
        return True
    allowed = _configured_allowed_origins()
    if not allowed:
        return False
    return origin in allowed


def _is_authorized(request: Request) -> tuple[bool, str | None]:
    configured = _configured_auth_token()
    if configured is None:
        return False, "misconfigured"
    supplied = _extract_supplied_token(request)
    if supplied != configured:
        return False, "unauthorized"
    return True, None


def _oauth_www_authenticate_header() -> str:
    return (
        'Bearer realm="nightledger-mcp", '
        'error="invalid_token", '
        'resource_metadata="/.well-known/oauth-protected-resource"'
    )


def _error_with_data(
    *,
    message_id: Any,
    code: int,
    message: str,
    envelope_code: str,
    envelope_message: str,
) -> dict[str, Any]:
    response = error_response(message_id, code=code, message=message)
    response["error"]["data"] = {
        "error": {
            "code": envelope_code,
            "message": envelope_message,
            "details": [],
        }
    }
    return response


def _sse_payload(*, data: str, event: str = "message") -> str:
    return f"event: {event}\ndata: {data}\n\n"


def _session_id(request: Request) -> str | None:
    session_id = request.headers.get(_MCP_SESSION_HEADER, "").strip()
    if session_id == "":
        return None
    return session_id


def _validate_session_request(request: Request) -> tuple[bool, JSONResponse | None]:
    session_id = _session_id(request)
    if session_id is None:
        return False, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_SESSION_REQUIRED_CODE,
                message="Session required",
                envelope_code="SESSION_REQUIRED",
                envelope_message="Call initialize first and include MCP-Session-Id.",
            ),
        )
    if session_id not in _sessions:
        return False, JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_SESSION_NOT_FOUND_CODE,
                message="Session not found",
                envelope_code="SESSION_NOT_FOUND",
                envelope_message="Provided MCP session id is unknown.",
            ),
        )
    protocol_version = request.headers.get(_MCP_PROTOCOL_HEADER, "").strip()
    if protocol_version == "":
        return False, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_PROTOCOL_REQUIRED_CODE,
                message="MCP protocol version required",
                envelope_code="MCP_PROTOCOL_VERSION_REQUIRED",
                envelope_message="Include MCP-Protocol-Version for session requests.",
            ),
        )
    if protocol_version != _sessions[session_id]:
        return False, JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                None,
                code=-32600,
                message="Unsupported protocol version",
            ),
        )
    return True, None


def _wants_sse_response(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/event-stream" in accept


@app.get("/.well-known/oauth-protected-resource")
def oauth_protected_resource_metadata(request: Request) -> dict[str, Any]:
    servers = os.getenv(_REMOTE_AUTHORIZATION_SERVERS_ENV, "").strip()
    authorization_servers = [value.strip() for value in servers.split(",") if value.strip()]
    return {
        "resource": str(request.base_url).rstrip("/") + "/v1/mcp/remote",
        "authorization_servers": authorization_servers,
        "bearer_methods_supported": ["header"],
    }


@app.get("/v1/mcp/remote")
async def remote_mcp_stream(request: Request) -> Response:
    if not _origin_allowed(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_ORIGIN_FORBIDDEN_CODE,
                message="Forbidden origin",
                envelope_code="ORIGIN_FORBIDDEN",
                envelope_message="Origin is not allowed for MCP remote transport.",
            ),
        )
    authorized, failure_type = _is_authorized(request)
    if not authorized:
        if failure_type == "misconfigured":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=_error_with_data(
                    message_id=None,
                    code=_REMOTE_MISCONFIGURED_CODE,
                    message="Remote auth misconfigured",
                    envelope_code="REMOTE_AUTH_MISCONFIGURED",
                    envelope_message=(
                        "Remote MCP auth token is not configured. Set "
                        "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN."
                    ),
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_UNAUTHORIZED_CODE,
                message="Unauthorized",
                envelope_code="UNAUTHORIZED",
                envelope_message="Missing or invalid remote MCP auth token.",
            ),
            headers={"WWW-Authenticate": _oauth_www_authenticate_header()},
        )

    valid, error = _validate_session_request(request)
    if not valid and error is not None:
        return error

    session_id = _session_id(request)
    assert session_id is not None
    payload = _sse_payload(
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/ready",
                "params": {"session_id": session_id},
            },
            separators=(",", ":"),
        )
    )
    return StreamingResponse(iter([payload]), media_type="text/event-stream")


@app.post("/v1/mcp/remote")
async def remote_mcp_entrypoint(request: Request) -> Response:
    if not _origin_allowed(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_ORIGIN_FORBIDDEN_CODE,
                message="Forbidden origin",
                envelope_code="ORIGIN_FORBIDDEN",
                envelope_message="Origin is not allowed for MCP remote transport.",
            ),
        )

    authorized, failure_type = _is_authorized(request)
    if not authorized:
        if failure_type == "misconfigured":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=_error_with_data(
                    message_id=None,
                    code=_REMOTE_MISCONFIGURED_CODE,
                    message="Remote auth misconfigured",
                    envelope_code="REMOTE_AUTH_MISCONFIGURED",
                    envelope_message=(
                        "Remote MCP auth token is not configured. Set "
                        "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN."
                    ),
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_UNAUTHORIZED_CODE,
                message="Unauthorized",
                envelope_code="UNAUTHORIZED",
                envelope_message="Missing or invalid remote MCP auth token.",
            ),
            headers={"WWW-Authenticate": _oauth_www_authenticate_header()},
        )

    try:
        body = await request.body()
        decoded = body.decode("utf-8")
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(None, code=-32700, message="Parse error"),
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(None, code=-32600, message="Invalid Request"),
        )

    method = payload.get("method")
    if method != "initialize":
        valid, error = _validate_session_request(request)
        if not valid and error is not None:
            return error

    response = _server.handle_message(payload)
    if response is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    headers: dict[str, str] = {}
    if method == "initialize":
        session_id = uuid4().hex
        _sessions[session_id] = _MCP_PROTOCOL_VERSION
        headers[_MCP_SESSION_HEADER] = session_id

    if _wants_sse_response(request):
        body = _sse_payload(data=json.dumps(response, separators=(",", ":")))
        return StreamingResponse(iter([body]), media_type="text/event-stream", headers=headers)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response, headers=headers)


@app.delete("/v1/mcp/remote")
async def remote_mcp_delete(request: Request) -> Response:
    if not _origin_allowed(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_ORIGIN_FORBIDDEN_CODE,
                message="Forbidden origin",
                envelope_code="ORIGIN_FORBIDDEN",
                envelope_message="Origin is not allowed for MCP remote transport.",
            ),
        )
    authorized, failure_type = _is_authorized(request)
    if not authorized:
        if failure_type == "misconfigured":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=_error_with_data(
                    message_id=None,
                    code=_REMOTE_MISCONFIGURED_CODE,
                    message="Remote auth misconfigured",
                    envelope_code="REMOTE_AUTH_MISCONFIGURED",
                    envelope_message=(
                        "Remote MCP auth token is not configured. Set "
                        "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN."
                    ),
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_with_data(
                message_id=None,
                code=_REMOTE_UNAUTHORIZED_CODE,
                message="Unauthorized",
                envelope_code="UNAUTHORIZED",
                envelope_message="Missing or invalid remote MCP auth token.",
            ),
            headers={"WWW-Authenticate": _oauth_www_authenticate_header()},
        )
    valid, error = _validate_session_request(request)
    if not valid and error is not None:
        return error
    session_id = _session_id(request)
    assert session_id is not None
    _sessions.pop(session_id, None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
