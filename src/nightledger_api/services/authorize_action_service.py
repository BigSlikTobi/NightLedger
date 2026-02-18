import json
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


AuthorizeActionState = Literal["allow", "requires_approval", "deny"]


class AuthorizeActionIntent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["purchase.create"]


class AuthorizeActionContext(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    transport_decision_hint: AuthorizeActionState | None = None


class AuthorizeActionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    intent: AuthorizeActionIntent
    context: AuthorizeActionContext


def evaluate_authorize_action(payload: AuthorizeActionRequest) -> dict[str, str]:
    state = payload.context.transport_decision_hint or "allow"
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
        "allow": "TRANSPORT_CONTRACT_ACCEPTED",
        "requires_approval": "TRANSPORT_REQUIRES_APPROVAL",
        "deny": "TRANSPORT_DENIED",
    }
    return mapping[state]
