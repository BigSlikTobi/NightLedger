from datetime import datetime, timedelta, timezone

import pytest

from nightledger_api.services.errors import (
    ExecutionActionMismatchError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
)
from nightledger_api.services.execution_token_service import (
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
        secret="test-secret",
        ttl_seconds=300,
    )

    claims = verify_execution_token(
        token=token,
        expected_action="purchase.create",
        now=_now(),
        secret="test-secret",
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
        secret="test-secret",
        ttl_seconds=300,
    )
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(ExecutionTokenInvalidError):
        verify_execution_token(
            token=tampered,
            expected_action="purchase.create",
            now=_now(),
            secret="test-secret",
        )


def test_verify_execution_token_rejects_expired_token() -> None:
    issued_at = _now()
    token, _ = mint_execution_token(
        decision_id="dec_round2_expired",
        action="purchase.create",
        now=issued_at,
        secret="test-secret",
        ttl_seconds=1,
    )

    with pytest.raises(ExecutionTokenExpiredError):
        verify_execution_token(
            token=token,
            expected_action="purchase.create",
            now=issued_at + timedelta(seconds=2),
            secret="test-secret",
        )


def test_verify_execution_token_rejects_action_mismatch() -> None:
    token, _ = mint_execution_token(
        decision_id="dec_round2_action",
        action="purchase.create",
        now=_now(),
        secret="test-secret",
        ttl_seconds=300,
    )

    with pytest.raises(ExecutionActionMismatchError):
        verify_execution_token(
            token=token,
            expected_action="transfer.create",
            now=_now(),
            secret="test-secret",
        )
