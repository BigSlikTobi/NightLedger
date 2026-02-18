from datetime import datetime
from typing import Any

from nightledger_api.services.errors import ApprovalNotFoundError, InconsistentRunStateError
from nightledger_api.services.event_store import EventStore, StoredEvent, _build_event_hash


def export_decision_audit(*, store: EventStore, decision_id: str) -> dict[str, Any]:
    matching_events = [
        event
        for event in store.list_all()
        if _decision_id(event) == decision_id
    ]
    if not matching_events:
        raise ApprovalNotFoundError(event_id=decision_id, detail_path="decision_id")

    run_ids = sorted({event.run_id for event in matching_events})
    if len(run_ids) > 1:
        raise InconsistentRunStateError(
            detail_path="decision_id",
            detail_message="decision_id spans multiple runs and cannot be exported deterministically",
            detail_code="CROSS_RUN_DECISION_TRACE",
            detail_type="state_conflict",
        )

    run_id = run_ids[0]
    run_events = store.list_by_run_id(run_id)
    _verify_hash_chain(events=run_events)
    ordered = [event for event in run_events if _decision_id(event) == decision_id]

    return {
        "decision_id": decision_id,
        "run_id": run_id,
        "event_count": len(ordered),
        "events": [
            {
                "event_id": event.id,
                "decision_id": decision_id,
                "action_type": str(event.payload.get("type", "")),
                "actor": str(event.payload.get("actor", "")),
                "timestamp": _format_timestamp(event.timestamp),
                "reason": str(event.payload.get("details", "")),
                "prev_hash": event.prev_hash,
                "hash": event.hash,
            }
            for event in ordered
        ],
    }


def _verify_hash_chain(*, events: list[StoredEvent]) -> None:
    previous_hash: str | None = None
    for event in events:
        expected_hash = _build_event_hash(
            run_id=event.run_id,
            event_id=event.id,
            timestamp=event.timestamp.isoformat(),
            payload=event.payload,
            integrity_warning=event.integrity_warning,
            prev_hash=previous_hash,
        )
        if (
            event.prev_hash != previous_hash
            or not event.hash
            or event.hash != expected_hash
        ):
            raise InconsistentRunStateError(
                detail_path="hash",
                detail_message="stored hash chain integrity validation failed",
                detail_code="HASH_CHAIN_BROKEN",
                detail_type="state_conflict",
            )
        previous_hash = event.hash


def _decision_id(event: StoredEvent) -> str | None:
    approval = event.payload.get("approval")
    if not isinstance(approval, dict):
        return None
    decision_id = approval.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id:
        return None
    return decision_id


def _format_timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
