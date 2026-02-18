import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from nightledger_api.services.errors import (
    ExecutionActionMismatchError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
)

_EXECUTION_TOKEN_SECRET_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_SECRET"
_EXECUTION_TOKEN_TTL_SECONDS_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_TTL_SECONDS"
_DEFAULT_EXECUTION_TOKEN_SECRET = "nightledger-dev-secret-change-me"
_DEFAULT_EXECUTION_TOKEN_TTL_SECONDS = 300


def mint_execution_token(
    *,
    decision_id: str,
    action: str,
    now: datetime | None = None,
    secret: str | None = None,
    ttl_seconds: int | None = None,
) -> tuple[str, str]:
    issued_at = _normalize_now(now)
    token_secret = secret if secret is not None else configured_execution_token_secret()
    ttl = ttl_seconds if ttl_seconds is not None else configured_execution_token_ttl_seconds()
    expires_at = issued_at + timedelta(seconds=ttl)

    payload = {
        "decision_id": decision_id,
        "action": action,
        "exp": int(expires_at.timestamp()),
        "jti": f"jti_{uuid4().hex}",
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    signature = hmac.new(token_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}", expires_at.isoformat().replace("+00:00", "Z")


def verify_execution_token(
    *,
    token: str,
    expected_action: str,
    now: datetime | None = None,
    secret: str | None = None,
) -> dict[str, str | int]:
    token_secret = secret if secret is not None else configured_execution_token_secret()
    issued_at = _normalize_now(now)

    parts = token.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ExecutionTokenInvalidError()
    payload_b64, provided_signature_b64 = parts

    expected_signature = hmac.new(
        token_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
    ).digest()
    expected_signature_b64 = _b64url_encode(expected_signature)
    if not hmac.compare_digest(provided_signature_b64, expected_signature_b64):
        raise ExecutionTokenInvalidError()

    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise ExecutionTokenInvalidError() from None

    action = payload.get("action")
    decision_id = payload.get("decision_id")
    exp = payload.get("exp")
    jti = payload.get("jti")
    if not isinstance(action, str) or not isinstance(decision_id, str) or not isinstance(exp, int) or not isinstance(jti, str):
        raise ExecutionTokenInvalidError()

    if action != expected_action:
        raise ExecutionActionMismatchError(expected_action=expected_action, token_action=action)

    if int(issued_at.timestamp()) >= exp:
        raise ExecutionTokenExpiredError()

    exp_iso = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "decision_id": decision_id,
        "action": action,
        "exp": exp,
        "exp_iso": exp_iso,
        "jti": jti,
    }


def configured_execution_token_secret() -> str:
    configured = os.getenv(_EXECUTION_TOKEN_SECRET_ENV)
    if configured is None:
        return _DEFAULT_EXECUTION_TOKEN_SECRET
    value = configured.strip()
    if value == "":
        return _DEFAULT_EXECUTION_TOKEN_SECRET
    return value


def configured_execution_token_ttl_seconds() -> int:
    configured = os.getenv(_EXECUTION_TOKEN_TTL_SECONDS_ENV)
    if configured is None:
        return _DEFAULT_EXECUTION_TOKEN_TTL_SECONDS
    try:
        value = int(configured)
        if value <= 0:
            return _DEFAULT_EXECUTION_TOKEN_TTL_SECONDS
        return value
    except ValueError:
        return _DEFAULT_EXECUTION_TOKEN_TTL_SECONDS


def _normalize_now(now: datetime | None) -> datetime:
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
