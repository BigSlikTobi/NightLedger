from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    DuplicateApprovalError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    StorageWriteError,
)
from nightledger_api.services.event_ingest_service import validate_event_payload
from nightledger_api.services.event_store import EventStore, StoredEvent
from nightledger_api.services.run_status_service import project_run_status

ApprovalDecision = Literal["approved", "rejected"]


def list_pending_approvals(store: EventStore) -> dict[str, Any]:
    all_events = store.list_all()
    run_ids = sorted({event.run_id for event in all_events})
    approvals: list[dict[str, Any]] = []

    for run_id in run_ids:
        run_events = store.list_by_run_id(run_id)
        projection = project_run_status(run_events)
        pending_context = projection.pending_approval
        if projection.status != "paused" or pending_context is None:
            continue

        pending_event_id = pending_context["event_id"]
        pending_event = _find_event_by_id(run_events, pending_event_id)
        if pending_event is None:
            raise InconsistentRunStateError(
                detail_path="approval",
                detail_message="pending approval event not found in run timeline",
                detail_code="MISSING_PENDING_EVENT",
                detail_type="state_conflict",
            )

        payload = pending_event.payload
        approvals.append(
            {
                "event_id": pending_event.id,
                "run_id": pending_event.run_id,
                "requested_at": pending_context["requested_at"],
                "requested_by": pending_context["requested_by"],
                "title": payload.get("title"),
                "details": payload.get("details"),
                "reason": pending_context["reason"],
                "risk_level": payload.get("risk_level"),
            }
        )

    approvals.sort(key=lambda item: (item["requested_at"], item["event_id"]))
    return {"pending_count": len(approvals), "approvals": approvals}


def resolve_pending_approval(
    *,
    store: EventStore,
    event_id: str,
    decision: ApprovalDecision,
    approver_id: str,
    reason: str | None,
) -> dict[str, Any]:
    all_events = store.list_all()
    matches = [event for event in all_events if event.id == event_id]

    if not matches:
        raise ApprovalNotFoundError(event_id=event_id)
    if len(matches) > 1:
        raise AmbiguousEventIdError(event_id=event_id)

    target_event = matches[0]
    run_events = store.list_by_run_id(target_event.run_id)

    if not _is_pending_signal(target_event):
        raise NoPendingApprovalError(event_id=event_id)

    if _was_event_resolved(run_events, event_id):
        raise DuplicateApprovalError(event_id=event_id)

    projection = project_run_status(run_events)

    pending_context = projection.pending_approval
    if projection.status == "paused" and pending_context is not None:
        if pending_context.get("event_id") == event_id:
            return _append_resolution_event(
                store=store,
                target_event=target_event,
                run_events=run_events,
                decision=decision,
                approver_id=approver_id,
                reason=reason,
        )
        raise NoPendingApprovalError(event_id=event_id)

    raise NoPendingApprovalError(event_id=event_id)


def _append_resolution_event(
    *,
    store: EventStore,
    target_event: StoredEvent,
    run_events: list[StoredEvent],
    decision: ApprovalDecision,
    approver_id: str,
    reason: str | None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    latest_run_timestamp = max(event.timestamp for event in run_events)
    min_resolution_time = latest_run_timestamp + timedelta(milliseconds=1)
    resolved_time = now if now > min_resolution_time else min_resolution_time
    resolved_at = _format_timestamp(resolved_time)
    meta_step = "approval_approved" if decision == "approved" else "approval_rejected"
    approval_data = target_event.payload.get("approval", {})
    title = "Approval approved" if decision == "approved" else "Approval rejected"
    details = reason if reason and reason.strip() else f"{title} by {approver_id}"

    payload_dict: dict[str, Any] = {
        "id": _build_resolution_event_id(
            target_event_id=target_event.id,
            decision=decision,
            timestamp=resolved_at,
        ),
        "run_id": target_event.run_id,
        "timestamp": resolved_at,
        "type": "approval_resolved",
        "actor": "human",
        "title": title,
        "details": details,
        "confidence": target_event.payload.get("confidence"),
        "risk_level": target_event.payload.get("risk_level"),
        "requires_approval": True,
        "approval": {
            "status": decision,
            "requested_by": approval_data.get("requested_by"),
            "resolved_by": approver_id,
            "resolved_at": resolved_at,
            "reason": reason,
        },
        "evidence": [],
        "meta": {"workflow": "approval_gate", "step": meta_step},
    }

    payload = validate_event_payload(payload_dict)
    try:
        stored = store.append(payload)
    except StorageWriteError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageWriteError("storage backend append failed") from exc

    return {
        "status": "resolved",
        "event_id": stored.id,
        "target_event_id": target_event.id,
        "run_id": target_event.run_id,
        "decision": decision,
        "resolved_at": resolved_at,
    }


def _was_event_resolved(run_events: list[StoredEvent], target_event_id: str) -> bool:
    current_pending_event_id: str | None = None
    resolution_prefix = f"apr_{target_event_id}_"

    for event in run_events:
        if _is_pending_signal(event):
            current_pending_event_id = event.id
            continue
        if _is_resolution_signal(event):
            if event.id.startswith(resolution_prefix):
                return True
            if current_pending_event_id == target_event_id:
                return True
            current_pending_event_id = None

    return False


def _is_pending_signal(event: StoredEvent) -> bool:
    payload = event.payload
    approval = payload.get("approval", {})
    return event.payload.get("type") == "approval_requested" or (
        bool(payload.get("requires_approval", False))
        and approval.get("status") == "pending"
    )


def _is_resolution_signal(event: StoredEvent) -> bool:
    payload = event.payload
    approval = payload.get("approval", {})
    return payload.get("type") == "approval_resolved" or (
        bool(payload.get("requires_approval", False))
        and approval.get("status") in {"approved", "rejected"}
    )


def _find_event_by_id(events: list[StoredEvent], event_id: str) -> StoredEvent | None:
    for event in events:
        if event.id == event_id:
            return event
    return None


def _build_resolution_event_id(
    *, target_event_id: str, decision: ApprovalDecision, timestamp: str
) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").replace(".", "")
    compact_time = compact_time.replace("T", "T").replace("Z", "Z")
    return f"apr_{target_event_id}_{decision}_{compact_time}_{uuid4().hex[:8]}"


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
