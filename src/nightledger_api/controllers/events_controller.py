from typing import Any

from fastapi import APIRouter, Depends, status

from nightledger_api.services.event_ingest_service import validate_event_payload
from nightledger_api.services.event_store import EventStore, InMemoryAppendOnlyEventStore
from nightledger_api.services.errors import (
    DuplicateEventError,
    StorageReadError,
    StorageWriteError,
)


router = APIRouter()
_event_store = InMemoryAppendOnlyEventStore()


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
