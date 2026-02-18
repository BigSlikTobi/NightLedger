import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, ConfigDict, Field

from nightledger_api.services.approval_service import (
    get_approval_decision_state,
    list_pending_approvals,
    register_pending_approval_request,
    resolve_pending_approval_by_decision_id,
    resolve_pending_approval,
)
from nightledger_api.services.authorize_action_service import (
    AuthorizeActionContext,
    AuthorizeActionRequest,
    evaluate_authorize_action,
)
from nightledger_api.services.audit_export_service import export_decision_audit
from nightledger_api.services.business_rules_service import validate_event_business_rules
from nightledger_api.services.event_ingest_service import validate_event_payload
from nightledger_api.services.event_store import (
    EventStore,
    InMemoryAppendOnlyEventStore,
    SQLiteAppendOnlyEventStore,
)
from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    BusinessRuleValidationError,
    DuplicateApprovalError,
    DuplicateEventError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    RunNotFoundError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
    ExecutionActionMismatchError,
    ExecutionDecisionNotApprovedError,
    ExecutionPayloadMismatchError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
    ExecutionTokenMissingError,
    ExecutionTokenReplayedError,
)
from nightledger_api.services.execution_token_service import (
    build_purchase_payload_hash,
    mint_execution_token,
    verify_execution_token,
)
from nightledger_api.services.execution_replay_store import SQLiteExecutionReplayStore
from nightledger_api.services.journal_projection_service import project_run_journal
from nightledger_api.services.run_status_service import project_run_status


router = APIRouter()
_EVENT_STORE_BACKEND_ENV = "NIGHTLEDGER_EVENT_STORE_BACKEND"
_EVENT_STORE_DB_PATH_ENV = "NIGHTLEDGER_EVENT_STORE_DB_PATH"
_DEFAULT_EVENT_STORE_BACKEND = "memory"
_DEFAULT_EVENT_STORE_DB_PATH = "/tmp/nightledger_events.db"
_event_store: EventStore | None = None
logger = logging.getLogger(__name__)
uvicorn_logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)
uvicorn_logger.setLevel(logging.INFO)
_execution_replay_store = SQLiteExecutionReplayStore()


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    decision: Literal["approved", "rejected"]
    approver_id: str = Field(min_length=1)
    reason: str | None = None


class ApprovalRequestRegistrationPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    decision_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str = Field(min_length=1)
    risk_level: Literal["low", "medium", "high"]
    reason: str | None = None


class PurchaseCreateExecutionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    run_id: str | None = None
    amount: float = Field(gt=0)
    currency: Literal["EUR"]
    merchant: str = Field(min_length=1)


class ExecutionTokenMintRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: float = Field(gt=0)
    currency: Literal["EUR"]
    merchant: str = Field(min_length=1)


def get_event_store() -> EventStore:
    global _event_store
    if _event_store is None:
        _event_store = _build_event_store()
    return _event_store


def _reset_event_store() -> EventStore:
    global _event_store
    _event_store = _build_event_store()
    return _event_store


def _build_event_store() -> EventStore:
    backend = os.getenv(_EVENT_STORE_BACKEND_ENV, _DEFAULT_EVENT_STORE_BACKEND).strip().lower()
    if backend == "sqlite":
        path = os.getenv(_EVENT_STORE_DB_PATH_ENV, _DEFAULT_EVENT_STORE_DB_PATH).strip()
        return SQLiteAppendOnlyEventStore(path=path or _DEFAULT_EVENT_STORE_DB_PATH)
    return InMemoryAppendOnlyEventStore()


def _triage_inbox_seed_payloads() -> list[dict[str, Any]]:
    run_id = "run_triage_inbox_demo_1"
    return [
        {
            "id": "evt_triage_inbox_001",
            "run_id": run_id,
            "timestamp": "2026-02-16T08:00:00Z",
            "type": "intent",
            "actor": "agent",
            "title": "Begin triage_inbox run",
            "details": "Agent starts inbox triage workflow.",
            "confidence": 0.92,
            "risk_level": "low",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [{"kind": "log", "label": "Workflow start", "ref": "log://triage-inbox/001"}],
            "meta": {"workflow": "triage_inbox", "step": "start"},
        },
        {
            "id": "evt_triage_inbox_002",
            "run_id": run_id,
            "timestamp": "2026-02-16T08:00:10Z",
            "type": "action",
            "actor": "agent",
            "title": "Draft high-priority response",
            "details": "Agent drafts a response and flags potential refund action.",
            "confidence": 0.87,
            "risk_level": "medium",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [{"kind": "diff", "label": "Draft response diff", "ref": "diff://triage-inbox/002"}],
            "meta": {"workflow": "triage_inbox", "step": "draft_response"},
        },
        {
            "id": "evt_triage_inbox_003",
            "run_id": run_id,
            "timestamp": "2026-02-16T08:00:20Z",
            "type": "approval_requested",
            "actor": "agent",
            "title": "Approval required before sending refund",
            "details": "Refund exceeds auto-approval threshold and requires human sign-off.",
            "confidence": 0.81,
            "risk_level": "high",
            "requires_approval": True,
            "approval": {
                "status": "pending",
                "requested_by": "agent",
                "resolved_by": None,
                "resolved_at": None,
                "reason": "Refund amount exceeds policy threshold",
            },
            "evidence": [{"kind": "artifact", "label": "Refund request packet", "ref": "artifact://triage-inbox/003"}],
            "meta": {"workflow": "triage_inbox", "step": "approval_gate"},
        },
    ]


@router.post("/v1/demo/triage_inbox/reset-seed", status_code=status.HTTP_200_OK)
def reset_seed_triage_inbox_demo() -> dict[str, Any]:
    store = _reset_event_store()
    seeded_event_ids: list[str] = []
    payloads = _triage_inbox_seed_payloads()
    try:
        for payload in payloads:
            event = validate_event_payload(payload)
            stored = store.append(event)
            seeded_event_ids.append(stored.id)
    except (SchemaValidationError, DuplicateEventError) as exc:
        _log_demo_seed_failure(exc=exc, payloads=payloads)
        raise
    except StorageWriteError as exc:
        _log_demo_seed_failure(exc=exc, payloads=payloads)
        raise
    except Exception as exc:
        _log_demo_seed_failure(exc=exc, payloads=payloads)
        raise StorageWriteError("demo reset-seed failed") from exc
    return {
        "status": "seeded",
        "workflow": "triage_inbox",
        "run_id": "run_triage_inbox_demo_1",
        "event_count": len(seeded_event_ids),
        "seeded_event_ids": seeded_event_ids,
    }


def _log_demo_seed_failure(*, exc: Exception, payloads: list[dict[str, Any]]) -> None:
    logger.error(
        json.dumps(
            {
                "event": "demo_seed_failed",
                "workflow": "triage_inbox",
                "event_ids": [str(payload.get("id", "")) for payload in payloads],
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }
        ),
        exc_info=True,
    )


def _log_approval_resolution_requested(
    *,
    event_id: str,
    decision: str,
    approver_id: str,
) -> None:
    _log_structured(
        logging.INFO,
        {
            "event": "approval_resolution_requested",
            "target_event_id": event_id,
            "decision": decision,
            "approver_id": approver_id,
        },
    )


def _log_approval_resolution_completed(
    *,
    event_id: str,
    decision: str,
    approver_id: str,
    result: dict[str, Any],
) -> None:
    orchestration = result.get("orchestration", {})
    timing = result.get("timing", {})
    _log_structured(
        logging.INFO,
        {
            "event": "approval_resolution_completed",
            "target_event_id": event_id,
            "decision": decision,
            "approver_id": approver_id,
            "run_id": result.get("run_id"),
            "run_status": result.get("run_status"),
            "orchestration_applied": orchestration.get("applied"),
            "orchestration_event_ids": orchestration.get("event_ids", []),
            "state_transition": timing.get("state_transition"),
        },
    )


def _log_approval_resolution_failed(
    *,
    event_id: str,
    decision: str,
    approver_id: str,
    exc: Exception,
) -> None:
    _log_structured(
        logging.WARNING,
        {
            "event": "approval_resolution_failed",
            "target_event_id": event_id,
            "decision": decision,
            "approver_id": approver_id,
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        },
        exc_info=True,
    )


def _log_structured(level: int, payload: dict[str, Any], *, exc_info: bool = False) -> None:
    message = json.dumps(payload)
    logger.log(level, message, exc_info=exc_info)
    uvicorn_logger.log(level, message, exc_info=exc_info)


@router.post("/v1/mcp/authorize_action", status_code=status.HTTP_200_OK)
def authorize_action(
    payload: AuthorizeActionRequest,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    decision = evaluate_authorize_action(payload=payload)
    run_id = _context_run_id(context=payload.context, decision_id=decision["decision_id"])

    _append_runtime_receipt(
        store=store,
        run_id=run_id,
        event_type="decision",
        title="authorize_action decision recorded",
        details=(
            f"decision_id={decision['decision_id']} "
            f"state={decision['state']} reason_code={decision['reason_code']}"
        ),
        decision_id=decision["decision_id"],
        step="authorize_action_decision",
    )
    if decision["state"] != "allow":
        return decision

    token, expires_at = mint_execution_token(
        decision_id=decision["decision_id"],
        action=payload.intent.action,
        run_id=run_id,
        payload_hash=build_purchase_payload_hash(
            amount=payload.context.amount,
            currency=payload.context.currency,
            merchant=_context_merchant(payload.context),
        ),
    )
    _append_runtime_receipt(
        store=store,
        run_id=run_id,
        event_type="decision",
        title="execution token minted",
        details=f"decision_id={decision['decision_id']} expires_at={expires_at}",
        decision_id=decision["decision_id"],
        step="execution_token_minted",
    )
    return {
        **decision,
        "execution_token": token,
        "execution_token_expires_at": expires_at,
    }


@router.post("/v1/events", status_code=status.HTTP_201_CREATED)
def ingest_event(
    payload: dict[str, Any], store: EventStore = Depends(get_event_store)
) -> dict[str, Any]:
    event = validate_event_payload(payload)
    try:
        existing_events = store.list_by_run_id(event.run_id)
        validate_event_business_rules(event=event, existing_events=existing_events)
        stored = store.append(event)
    except (
        BusinessRuleValidationError,
        DuplicateEventError,
        StorageReadError,
        StorageWriteError,
    ):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageWriteError("storage backend append failed") from exc
    return {
        "status": "accepted",
        "event_id": stored.id,
        "integrity_warning": stored.integrity_warning,
    }

@router.get("/v1/runs/{run_id}/events", status_code=status.HTTP_200_OK)
def get_run_events(
    run_id: str, store: EventStore = Depends(get_event_store)
) -> dict[str, Any]:
    try:
        events = store.list_by_run_id(run_id)
    except StorageReadError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc

    return {
        "run_id": run_id,
        "event_count": len(events),
        "events": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "run_id": event.run_id,
                "payload": event.payload,
                "integrity_warning": event.integrity_warning,
            }
            for event in events
        ],
    }


@router.get("/v1/runs/{run_id}/status", status_code=status.HTTP_200_OK)
def get_run_status(
    run_id: str, store: EventStore = Depends(get_event_store)
) -> dict[str, Any]:
    try:
        events = store.list_by_run_id(run_id)
    except StorageReadError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc

    if not events:
        raise RunNotFoundError(run_id=run_id)

    projection = project_run_status(events)
    return {
        "run_id": run_id,
        "status": projection.status,
        "pending_approval": projection.pending_approval,
    }


@router.get("/v1/runs/{run_id}/journal", status_code=status.HTTP_200_OK)
def get_run_journal(
    run_id: str, store: EventStore = Depends(get_event_store)
) -> dict[str, Any]:
    try:
        events = store.list_by_run_id(run_id)
    except StorageReadError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc

    if not events:
        raise RunNotFoundError(run_id=run_id)
    projection = project_run_journal(run_id=run_id, events=events)
    # Reuse run status projection as an approval-timeline consistency guard.
    project_run_status(events)
    return projection.to_dict()


@router.get("/v1/approvals/pending", status_code=status.HTTP_200_OK)
def get_pending_approvals(store: EventStore = Depends(get_event_store)) -> dict[str, Any]:
    try:
        return list_pending_approvals(store)
    except (StorageReadError, InconsistentRunStateError):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc


@router.post("/v1/approvals/requests", status_code=status.HTTP_200_OK)
def register_approval_request(
    payload: ApprovalRequestRegistrationPayload,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    try:
        return register_pending_approval_request(
            store=store,
            decision_id=payload.decision_id,
            run_id=payload.run_id,
            requested_by=payload.requested_by,
            title=payload.title,
            details=payload.details,
            risk_level=payload.risk_level,
            reason=payload.reason,
        )
    except (StorageReadError, StorageWriteError, DuplicateApprovalError):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageWriteError("storage backend append failed") from exc


@router.post("/v1/approvals/{event_id}", status_code=status.HTTP_200_OK)
def resolve_approval(
    event_id: str,
    payload: ApprovalDecisionRequest,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    _log_approval_resolution_requested(
        event_id=event_id,
        decision=payload.decision,
        approver_id=payload.approver_id,
    )
    try:
        result = resolve_pending_approval(
            store=store,
            event_id=event_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            reason=payload.reason,
        )
        _log_approval_resolution_completed(
            event_id=event_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            result=result,
        )
        return result
    except (
        StorageReadError,
        StorageWriteError,
        ApprovalNotFoundError,
        AmbiguousEventIdError,
        NoPendingApprovalError,
        DuplicateApprovalError,
        InconsistentRunStateError,
    ) as exc:
        _log_approval_resolution_failed(
            event_id=event_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            exc=exc,
        )
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc


@router.post("/v1/approvals/decisions/{decision_id}", status_code=status.HTTP_200_OK)
def resolve_approval_by_decision_id(
    decision_id: str,
    payload: ApprovalDecisionRequest,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    _log_approval_resolution_requested(
        event_id=decision_id,
        decision=payload.decision,
        approver_id=payload.approver_id,
    )
    try:
        result = resolve_pending_approval_by_decision_id(
            store=store,
            decision_id=decision_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            reason=payload.reason,
        )
        _log_approval_resolution_completed(
            event_id=decision_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            result=result,
        )
        return result
    except (
        StorageReadError,
        StorageWriteError,
        ApprovalNotFoundError,
        AmbiguousEventIdError,
        NoPendingApprovalError,
        DuplicateApprovalError,
        InconsistentRunStateError,
    ) as exc:
        _log_approval_resolution_failed(
            event_id=decision_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            exc=exc,
        )
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc


@router.get("/v1/approvals/decisions/{decision_id}", status_code=status.HTTP_200_OK)
def get_approval_by_decision_id(
    decision_id: str,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    try:
        return get_approval_decision_state(store=store, decision_id=decision_id)
    except (
        StorageReadError,
        ApprovalNotFoundError,
    ):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc


@router.get("/v1/approvals/decisions/{decision_id}/audit-export", status_code=status.HTTP_200_OK)
def get_decision_audit_export(
    decision_id: str,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    try:
        return export_decision_audit(store=store, decision_id=decision_id)
    except (
        StorageReadError,
        ApprovalNotFoundError,
        InconsistentRunStateError,
    ):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc


@router.post("/v1/executors/purchase.create", status_code=status.HTTP_200_OK)
def execute_purchase_create(
    payload: PurchaseCreateExecutionRequest,
    store: EventStore = Depends(get_event_store),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    try:
        claims = verify_execution_token(
            token=token,
            expected_action="purchase.create",
            expected_payload_hash=build_purchase_payload_hash(
                amount=payload.amount,
                currency=payload.currency,
                merchant=payload.merchant,
            ),
        )
    except (
        ExecutionTokenInvalidError,
        ExecutionTokenExpiredError,
        ExecutionActionMismatchError,
        ExecutionPayloadMismatchError,
    ) as exc:
        run_id = payload.run_id or "run_execution_gate_unscoped"
        _append_runtime_receipt(
            store=store,
            run_id=run_id,
            event_type="error",
            title="purchase.create blocked",
            details=f"code={_error_code_for_exception(exc)}",
            decision_id=None,
            step="execution_blocked",
        )
        raise
    run_id = _claim_run_id(claims=claims, fallback_run_id=payload.run_id)
    jti = str(claims["jti"])
    consumed = _execution_replay_store.consume_once(
        jti=jti,
        exp_unix=int(claims["exp"]),
    )
    if not consumed:
        _append_runtime_receipt(
            store=store,
            run_id=run_id,
            event_type="error",
            title="purchase.create blocked",
            details="code=EXECUTION_TOKEN_REPLAYED",
            decision_id=str(claims["decision_id"]),
            step="execution_blocked",
        )
        raise ExecutionTokenReplayedError()

    execution_id = f"exec_{uuid4().hex[:16]}"
    executed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _append_runtime_receipt(
        store=store,
        run_id=run_id,
        event_type="action",
        title="purchase.create executed",
        details=(
            f"decision_id={claims['decision_id']} execution_id={execution_id} "
            f"amount={payload.amount} currency={payload.currency} merchant={payload.merchant}"
        ),
        decision_id=str(claims["decision_id"]),
        step="purchase_executed",
    )
    return {
        "status": "executed",
        "action": "purchase.create",
        "decision_id": claims["decision_id"],
        "execution_id": execution_id,
        "executed_at": executed_at,
    }


@router.post("/v1/approvals/decisions/{decision_id}/execution-token", status_code=status.HTTP_200_OK)
def mint_execution_token_for_decision(
    decision_id: str,
    payload: ExecutionTokenMintRequest,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    state = get_approval_decision_state(store=store, decision_id=decision_id)
    if state["status"] != "approved":
        raise ExecutionDecisionNotApprovedError(decision_id=decision_id)

    token, expires_at = mint_execution_token(
        decision_id=decision_id,
        action="purchase.create",
        run_id=state["run_id"],
        payload_hash=build_purchase_payload_hash(
            amount=payload.amount,
            currency=payload.currency,
            merchant=payload.merchant,
        ),
    )
    _append_runtime_receipt(
        store=store,
        run_id=str(state["run_id"]),
        event_type="decision",
        title="execution token minted",
        details=f"decision_id={decision_id} expires_at={expires_at}",
        decision_id=decision_id,
        step="execution_token_minted",
    )
    return {
        "decision_id": decision_id,
        "action": "purchase.create",
        "execution_token": token,
        "expires_at": expires_at,
    }


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise ExecutionTokenMissingError()
    value = authorization.strip()
    if not value:
        raise ExecutionTokenMissingError()
    prefix = "bearer "
    if not value.lower().startswith(prefix):
        raise ExecutionTokenMissingError()
    token = value[len(prefix) :].strip()
    if not token:
        raise ExecutionTokenMissingError()
    return token


def _context_merchant(context: AuthorizeActionContext) -> str | None:
    merchant = _context_extra_value(context=context, key="merchant")
    if merchant is None:
        return None
    if isinstance(merchant, str):
        value = merchant.strip()
        return value if value else None
    return str(merchant)


def _context_run_id(*, context: AuthorizeActionContext, decision_id: str) -> str:
    run_id = _context_extra_value(context=context, key="run_id")
    if isinstance(run_id, str) and run_id.strip():
        return run_id.strip()
    request_id = _context_extra_value(context=context, key="request_id")
    if isinstance(request_id, str) and request_id.strip():
        return f"run_{request_id.strip()}"
    return f"run_{decision_id}"


def _context_extra_value(*, context: AuthorizeActionContext, key: str) -> Any:
    extras = getattr(context, "model_extra", None)
    if isinstance(extras, dict):
        return extras.get(key)
    return None


def _claim_run_id(*, claims: dict[str, Any], fallback_run_id: str | None) -> str:
    claimed = claims.get("run_id")
    if isinstance(claimed, str) and claimed.strip():
        return claimed
    if fallback_run_id is not None and fallback_run_id.strip():
        return fallback_run_id.strip()
    return f"run_{claims.get('decision_id', 'execution_gate')}"


def _append_runtime_receipt(
    *,
    store: EventStore,
    run_id: str,
    event_type: Literal["decision", "action", "error"],
    title: str,
    details: str,
    decision_id: str | None,
    step: str,
) -> None:
    now = datetime.now(timezone.utc)
    existing = store.list_by_run_id(run_id)
    if existing and now <= existing[-1].timestamp:
        now = existing[-1].timestamp + timedelta(milliseconds=1)

    event_payload = {
        "id": f"evt_runtime_{uuid4().hex[:16]}",
        "run_id": run_id,
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "type": event_type,
        "actor": "system",
        "title": title,
        "details": details,
        "confidence": 1.0,
        "risk_level": "low",
        "requires_approval": False,
        "approval": {
            "status": "not_required",
            "decision_id": decision_id,
            "requested_by": None,
            "resolved_by": None,
            "resolved_at": None,
            "reason": None,
        },
        "evidence": [],
        "meta": {
            "workflow": "execution_gate",
            "step": step,
        },
    }
    event = validate_event_payload(event_payload)
    store.append(event)


def _error_code_for_exception(exc: Exception) -> str:
    if isinstance(exc, ExecutionTokenInvalidError):
        return "EXECUTION_TOKEN_INVALID"
    if isinstance(exc, ExecutionTokenExpiredError):
        return "EXECUTION_TOKEN_EXPIRED"
    if isinstance(exc, ExecutionActionMismatchError):
        return "EXECUTION_ACTION_MISMATCH"
    if isinstance(exc, ExecutionPayloadMismatchError):
        return "EXECUTION_PAYLOAD_MISMATCH"
    return "EXECUTION_BLOCKED"
