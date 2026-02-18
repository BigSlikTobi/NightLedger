import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from nightledger_api.services.errors import (
    ExecutionActionMismatchError,
    ExecutionPayloadMismatchError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
    ExecutionTokenMisconfiguredError,
)

_EXECUTION_TOKEN_ACTIVE_KID_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_ACTIVE_KID"
_EXECUTION_TOKEN_KEYS_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_KEYS"
_EXECUTION_TOKEN_SECRET_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_SECRET"
_EXECUTION_TOKEN_TTL_SECONDS_ENV = "NIGHTLEDGER_EXECUTION_TOKEN_TTL_SECONDS"
_DEFAULT_EXECUTION_TOKEN_TTL_SECONDS = 300
_MIN_SECRET_LEN = 32


def mint_execution_token(
    *,
    decision_id: str,
    action: str,
    now: datetime | None = None,
    secret: str | None = None,
    ttl_seconds: int | None = None,
    payload_hash: str | None = None,
    run_id: str | None = None,
    kid: str | None = None,
) -> tuple[str, str]:
    issued_at = _normalize_now(now)
    ttl = ttl_seconds if ttl_seconds is not None else configured_execution_token_ttl_seconds()
    expires_at = issued_at + timedelta(seconds=ttl)

    resolved_kid, signing_secret = _resolve_signing_secret(secret=secret, kid=kid)

    payload: dict[str, str | int] = {
        "decision_id": decision_id,
        "action": action,
        "exp": int(expires_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "jti": f"jti_{uuid4().hex}",
        "kid": resolved_kid,
    }
    if payload_hash is not None:
        payload["payload_hash"] = payload_hash
    if run_id is not None and run_id.strip() != "":
        payload["run_id"] = run_id.strip()

    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    signature = hmac.new(signing_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}", expires_at.isoformat().replace("+00:00", "Z")


def verify_execution_token(
    *,
    token: str,
    expected_action: str,
    now: datetime | None = None,
    secret: str | None = None,
    expected_payload_hash: str | None = None,
    key_map: dict[str, str] | None = None,
) -> dict[str, str | int]:
    issued_at = _normalize_now(now)

    parts = token.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ExecutionTokenInvalidError()
    payload_b64, provided_signature_b64 = parts

    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise ExecutionTokenInvalidError() from None

    kid = payload.get("kid")
    if not isinstance(kid, str) or kid.strip() == "":
        raise ExecutionTokenInvalidError()

    verification_secret = _resolve_verification_secret(secret=secret, kid=kid, key_map=key_map)

    expected_signature = hmac.new(
        verification_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
    ).digest()
    expected_signature_b64 = _b64url_encode(expected_signature)
    if not hmac.compare_digest(provided_signature_b64, expected_signature_b64):
        raise ExecutionTokenInvalidError()

    action = payload.get("action")
    decision_id = payload.get("decision_id")
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    jti = payload.get("jti")
    token_payload_hash = payload.get("payload_hash")
    run_id = payload.get("run_id")

    if not isinstance(action, str) or not isinstance(decision_id, str) or not isinstance(exp, int):
        raise ExecutionTokenInvalidError()
    if not isinstance(nbf, int) or not isinstance(jti, str):
        raise ExecutionTokenInvalidError()
    if token_payload_hash is not None and not isinstance(token_payload_hash, str):
        raise ExecutionTokenInvalidError()
    if run_id is not None and not isinstance(run_id, str):
        raise ExecutionTokenInvalidError()

    now_ts = int(issued_at.timestamp())
    if now_ts < nbf:
        raise ExecutionTokenInvalidError()

    if action != expected_action:
        raise ExecutionActionMismatchError(expected_action=expected_action, token_action=action)

    if expected_payload_hash is not None and token_payload_hash != expected_payload_hash:
        raise ExecutionPayloadMismatchError()

    if now_ts >= exp:
        raise ExecutionTokenExpiredError()

    exp_iso = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "decision_id": decision_id,
        "action": action,
        "exp": exp,
        "exp_iso": exp_iso,
        "nbf": nbf,
        "jti": jti,
        "kid": kid,
        "payload_hash": token_payload_hash,
        "run_id": run_id,
    }


def build_purchase_payload_hash(*, amount: float, currency: str, merchant: str | None) -> str:
    canonical = {
        "amount": float(amount),
        "currency": currency,
        "merchant": merchant,
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def configured_execution_token_key_map() -> dict[str, str]:
    configured = os.getenv(_EXECUTION_TOKEN_KEYS_ENV)
    if configured is not None and configured.strip() != "":
        key_map: dict[str, str] = {}
        for raw in configured.split(","):
            pair = raw.strip()
            if pair == "" or ":" not in pair:
                raise ExecutionTokenMisconfiguredError(
                    message=(
                        "NIGHTLEDGER_EXECUTION_TOKEN_KEYS must use 'kid:secret' comma-separated format"
                    )
                )
            kid, secret = pair.split(":", 1)
            resolved_kid = kid.strip()
            resolved_secret = secret.strip()
            if resolved_kid == "" or resolved_secret == "":
                raise ExecutionTokenMisconfiguredError(
                    message="NIGHTLEDGER_EXECUTION_TOKEN_KEYS contains empty kid or secret"
                )
            _validate_secret_strength(resolved_secret)
            key_map[resolved_kid] = resolved_secret
        if not key_map:
            raise ExecutionTokenMisconfiguredError(
                message="NIGHTLEDGER_EXECUTION_TOKEN_KEYS did not contain usable keys"
            )
        return key_map

    legacy_secret = os.getenv(_EXECUTION_TOKEN_SECRET_ENV)
    if legacy_secret is None or legacy_secret.strip() == "":
        raise ExecutionTokenMisconfiguredError(
            message=(
                "Execution token secret is not configured. Set NIGHTLEDGER_EXECUTION_TOKEN_KEYS "
                "or NIGHTLEDGER_EXECUTION_TOKEN_SECRET"
            )
        )
    resolved = legacy_secret.strip()
    _validate_secret_strength(resolved)
    return {"v1": resolved}


def configured_execution_token_active_kid() -> str:
    configured = os.getenv(_EXECUTION_TOKEN_ACTIVE_KID_ENV)
    if configured is None or configured.strip() == "":
        return "v1"
    return configured.strip()


def _resolve_signing_secret(*, secret: str | None, kid: str | None) -> tuple[str, str]:
    if secret is not None:
        resolved_secret = secret.strip()
        _validate_secret_strength(resolved_secret)
        resolved_kid = kid if kid is not None else "inline"
        if resolved_kid.strip() == "":
            raise ExecutionTokenMisconfiguredError(message="Execution token kid must be non-empty")
        return resolved_kid.strip(), resolved_secret

    key_map = configured_execution_token_key_map()
    active_kid = configured_execution_token_active_kid()
    if active_kid not in key_map:
        raise ExecutionTokenMisconfiguredError(
            message=f"Active execution token kid '{active_kid}' not found in configured key map"
        )
    return active_kid, key_map[active_kid]


def _resolve_verification_secret(
    *,
    secret: str | None,
    kid: str,
    key_map: dict[str, str] | None,
) -> str:
    if secret is not None:
        _validate_secret_strength(secret)
        return secret

    resolved_key_map = key_map if key_map is not None else configured_execution_token_key_map()
    verification_secret = resolved_key_map.get(kid)
    if verification_secret is None:
        raise ExecutionTokenInvalidError()
    return verification_secret


def _validate_secret_strength(secret: str) -> None:
    if len(secret) < _MIN_SECRET_LEN:
        raise ExecutionTokenMisconfiguredError(
            message=(
                "Execution token secret is too short; minimum length is "
                f"{_MIN_SECRET_LEN} characters"
            )
        )


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
