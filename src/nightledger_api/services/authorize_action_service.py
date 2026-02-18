import json
import os
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


AuthorizeActionState = Literal["allow", "requires_approval", "deny"]
_DEFAULT_PURCHASE_APPROVAL_THRESHOLD_EUR = 100.0
_PURCHASE_APPROVAL_THRESHOLD_ENV = "NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR"


class AuthorizeActionIntent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["purchase.create"]


class AuthorizeActionContext(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    amount: float
    currency: Literal["EUR"]
    transport_decision_hint: AuthorizeActionState | None = None


class AuthorizeActionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    intent: AuthorizeActionIntent
    context: AuthorizeActionContext


def evaluate_authorize_action(payload: AuthorizeActionRequest) -> dict[str, str]:
    threshold = _configured_threshold_eur()
    state: AuthorizeActionState = (
        "requires_approval"
        if payload.context.amount > threshold
        else "allow"
    )
    return {
        "decision_id": _build_deterministic_decision_id(payload=payload),
        "state": state,
        "reason_code": _reason_code_for_state(state=state),
    }


def _build_deterministic_decision_id(*, payload: AuthorizeActionRequest) -> str:
    canonical_payload = {
        "intent": payload.intent.model_dump(mode="json"),
        "context": payload.context.model_dump(mode="json", exclude_none=True),
    }
    fingerprint = sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"dec_{fingerprint[:16]}"


def _reason_code_for_state(*, state: AuthorizeActionState) -> str:
    mapping = {
        "allow": "POLICY_ALLOW_WITHIN_THRESHOLD",
        "requires_approval": "AMOUNT_ABOVE_THRESHOLD",
        "deny": "POLICY_DENIED",
    }
    return mapping[state]


def _configured_threshold_eur() -> float:
    configured = os.getenv(_PURCHASE_APPROVAL_THRESHOLD_ENV)
    if configured is None:
        return _DEFAULT_PURCHASE_APPROVAL_THRESHOLD_EUR
    return float(configured)
