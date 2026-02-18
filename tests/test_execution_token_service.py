from datetime import datetime, timedelta, timezone

import pytest

from nightledger_api.services.errors import (
    ExecutionActionMismatchError,
    ExecutionPayloadMismatchError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
    ExecutionTokenMisconfiguredError,
)
from nightledger_api.services.execution_token_service import (
    build_purchase_payload_hash,
    mint_execution_token,
    verify_execution_token,
)


def _now() -> datetime:
    return datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_mint_and_verify_execution_token_round_trip() -> None:
    token, expires_at = mint_execution_token(
        decision_id="dec_round2_ok",
        action="purchase.create",
        now=_now(),
        secret="test-secret-key-material-32bytes!!",
        ttl_seconds=300,
    )

    claims = verify_execution_token(
        token=token,
        expected_action="purchase.create",
        now=_now(),
        secret="test-secret-key-material-32bytes!!",
    )

    assert claims["decision_id"] == "dec_round2_ok"
    assert claims["action"] == "purchase.create"
    assert claims["jti"]
    assert expires_at == claims["exp_iso"]


def test_verify_execution_token_rejects_tampered_token() -> None:
    token, _ = mint_execution_token(
        decision_id="dec_round2_tamper",
        action="purchase.create",
        now=_now(),
        secret="test-secret-key-material-32bytes!!",
        ttl_seconds=300,
    )
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(ExecutionTokenInvalidError):
        verify_execution_token(
            token=tampered,
            expected_action="purchase.create",
            now=_now(),
            secret="test-secret-key-material-32bytes!!",
        )


def test_verify_execution_token_rejects_expired_token() -> None:
    issued_at = _now()
    token, _ = mint_execution_token(
        decision_id="dec_round2_expired",
        action="purchase.create",
        now=issued_at,
        secret="test-secret-key-material-32bytes!!",
        ttl_seconds=1,
    )

    with pytest.raises(ExecutionTokenExpiredError):
        verify_execution_token(
            token=token,
            expected_action="purchase.create",
            now=issued_at + timedelta(seconds=2),
            secret="test-secret-key-material-32bytes!!",
        )


def test_verify_execution_token_rejects_action_mismatch() -> None:
    token, _ = mint_execution_token(
        decision_id="dec_round2_action",
        action="purchase.create",
        now=_now(),
        secret="test-secret-key-material-32bytes!!",
        ttl_seconds=300,
    )

    with pytest.raises(ExecutionActionMismatchError):
        verify_execution_token(
            token=token,
            expected_action="transfer.create",
            now=_now(),
            secret="test-secret-key-material-32bytes!!",
        )


def test_verify_execution_token_rejects_payload_hash_mismatch() -> None:
    token, _ = mint_execution_token(
        decision_id="dec_round2_payload",
        action="purchase.create",
        now=_now(),
        secret="test-secret-key-material-32bytes!!",
        ttl_seconds=300,
        payload_hash=build_purchase_payload_hash(
            amount=100,
            currency="EUR",
            merchant="ACME GmbH",
        ),
    )

    with pytest.raises(ExecutionPayloadMismatchError):
        verify_execution_token(
            token=token,
            expected_action="purchase.create",
            now=_now(),
            secret="test-secret-key-material-32bytes!!",
            expected_payload_hash=build_purchase_payload_hash(
                amount=999,
                currency="EUR",
                merchant="Mallory Corp",
            ),
        )


def test_mint_execution_token_requires_strong_secret_when_using_env(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_ACTIVE_KID", "v1")
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_KEYS", "v1:short-secret")

    with pytest.raises(ExecutionTokenMisconfiguredError):
        mint_execution_token(
            decision_id="dec_bad_secret",
            action="purchase.create",
            now=_now(),
        )


def test_verify_execution_token_supports_key_rotation_with_kid_lookup() -> None:
    token, _ = mint_execution_token(
        decision_id="dec_kid_rotation",
        action="purchase.create",
        now=_now(),
        secret="old-secret-key-material-32-bytes!!",
        ttl_seconds=300,
        kid="old",
    )

    claims = verify_execution_token(
        token=token,
        expected_action="purchase.create",
        now=_now(),
        key_map={
            "old": "old-secret-key-material-32-bytes!!",
            "new": "new-secret-key-material-32-bytes!!",
        },
    )

    assert claims["decision_id"] == "dec_kid_rotation"
