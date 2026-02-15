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
    StorageReadError,
    StorageWriteError,
)
from nightledger_api.services.journal_projection_service import project_run_journal
from nightledger_api.services.run_status_service import project_run_status


router = APIRouter()
_event_store = InMemoryAppendOnlyEventStore()


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    decision: Literal["approved", "rejected"]
    approver_id: str = Field(min_length=1)
    reason: str | None = None


def get_event_store() -> EventStore:
    return _event_store


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
    events = store.list_by_run_id(run_id)
    projection = project_run_journal(run_id=run_id, events=events)
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
