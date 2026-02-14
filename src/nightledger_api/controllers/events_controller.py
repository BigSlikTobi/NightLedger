from typing import Any

from fastapi import APIRouter, status

from nightledger_api.services.event_ingest_service import validate_event_payload

router = APIRouter()


@router.post("/v1/events", status_code=status.HTTP_201_CREATED)
def ingest_event(payload: dict[str, Any]) -> dict[str, str]:
    validate_event_payload(payload)
    return {"status": "accepted"}

