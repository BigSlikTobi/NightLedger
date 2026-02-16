import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from nightledger_api.services.approval_service import list_pending_approvals, resolve_pending_approval
from nightledger_api.services.event_ingest_service import validate_event_payload
from nightledger_api.services.event_store import EventStore, InMemoryAppendOnlyEventStore
from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    DuplicateApprovalError,
    DuplicateEventError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    RunNotFoundError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
)
from nightledger_api.services.journal_projection_service import project_run_journal
from nightledger_api.services.run_status_service import project_run_status


router = APIRouter()
_event_store = InMemoryAppendOnlyEventStore()
logger = logging.getLogger(__name__)


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    decision: Literal["approved", "rejected"]
    approver_id: str = Field(min_length=1)
    reason: str | None = None


def get_event_store() -> EventStore:
    return _event_store


def _reset_event_store() -> EventStore:
    global _event_store
    _event_store = InMemoryAppendOnlyEventStore()
    return _event_store


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


@router.post("/v1/events", status_code=status.HTTP_201_CREATED)
def ingest_event(
    payload: dict[str, Any], store: EventStore = Depends(get_event_store)
) -> dict[str, Any]:
    event = validate_event_payload(payload)
    try:
        stored = store.append(event)
    except (DuplicateEventError, StorageWriteError):
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


@router.post("/v1/approvals/{event_id}", status_code=status.HTTP_200_OK)
def resolve_approval(
    event_id: str,
    payload: ApprovalDecisionRequest,
    store: EventStore = Depends(get_event_store),
) -> dict[str, Any]:
    try:
        return resolve_pending_approval(
            store=store,
            event_id=event_id,
            decision=payload.decision,
            approver_id=payload.approver_id,
            reason=payload.reason,
        )
    except (
        StorageReadError,
        StorageWriteError,
        ApprovalNotFoundError,
        AmbiguousEventIdError,
        NoPendingApprovalError,
        DuplicateApprovalError,
        InconsistentRunStateError,
    ):
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageReadError("storage backend read failed") from exc
