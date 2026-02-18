from datetime import datetime, timedelta, timezone
from math import ceil
from time import perf_counter
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
_TRIAGE_INBOX_DEMO_RUN_ID = "run_triage_inbox_demo_1"
_TRIAGE_INBOX_DEMO_APPROVAL_EVENT_ID = "evt_triage_inbox_003"
_MVP_APPROVAL_TO_STATE_UPDATE_TARGET_MS = 1000


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
                "decision_id": payload.get("approval", {}).get("decision_id"),
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


def register_pending_approval_request(
    *,
    store: EventStore,
    decision_id: str,
    run_id: str,
    requested_by: str,
    title: str,
    details: str,
    risk_level: Literal["low", "medium", "high"],
    reason: str | None,
) -> dict[str, Any]:
    existing_decision_events = [
        event
        for event in store.list_all()
        if event.payload.get("approval", {}).get("decision_id") == decision_id
    ]
    lifecycle_events = [
        event
        for event in existing_decision_events
        if _is_pending_signal(event) or _is_resolution_signal(event)
    ]
    if lifecycle_events:
        latest_reason = "resolved"
        for event in lifecycle_events:
            if _is_pending_signal(event):
                latest_reason = "pending"
            elif _is_resolution_signal(event):
                latest_reason = "resolved"
        raise DuplicateApprovalError(
            event_id=decision_id,
            detail_path="decision_id",
            reason=latest_reason,
        )

    now = datetime.now(timezone.utc)
    run_events = store.list_by_run_id(run_id)
    if run_events:
        latest_run_timestamp = max(event.timestamp for event in run_events)
        if now <= latest_run_timestamp:
            now = latest_run_timestamp + timedelta(milliseconds=1)

    requested_at = _format_timestamp(now)
    event_id = _build_decision_pending_event_id(decision_id=decision_id, timestamp=requested_at)
    payload = validate_event_payload(
        {
            "id": event_id,
            "run_id": run_id,
            "timestamp": requested_at,
            "type": "approval_requested",
            "actor": "agent",
            "title": title,
            "details": details,
            "confidence": None,
            "risk_level": risk_level,
            "requires_approval": True,
            "approval": {
                "status": "pending",
                "decision_id": decision_id,
                "requested_by": requested_by,
                "resolved_by": None,
                "resolved_at": None,
                "reason": reason,
            },
            "evidence": [],
            "meta": {"workflow": "approval_gate", "step": "approval_requested"},
        }
    )
    try:
        stored = store.append(payload)
    except StorageWriteError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageWriteError("storage backend append failed") from exc

    return {
        "status": "registered",
        "decision_id": decision_id,
        "event_id": stored.id,
        "run_id": run_id,
        "approval_status": "pending",
    }


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
                initial_run_status=projection.status,
                decision=decision,
                approver_id=approver_id,
                reason=reason,
            )
        raise NoPendingApprovalError(event_id=event_id)

    raise NoPendingApprovalError(event_id=event_id)


def resolve_pending_approval_by_decision_id(
    *,
    store: EventStore,
    decision_id: str,
    decision: ApprovalDecision,
    approver_id: str,
    reason: str | None,
) -> dict[str, Any]:
    all_events = store.list_all()
    decision_events = [
        event
        for event in all_events
        if event.payload.get("approval", {}).get("decision_id") == decision_id
    ]
    if not decision_events:
        raise ApprovalNotFoundError(event_id=decision_id, detail_path="decision_id")

    pending_events = [event for event in decision_events if _is_pending_signal(event)]
    if len(pending_events) > 1:
        raise AmbiguousEventIdError(event_id=decision_id)
    if not pending_events:
        raise NoPendingApprovalError(event_id=decision_id)

    target_event = pending_events[0]
    result = resolve_pending_approval(
        store=store,
        event_id=target_event.id,
        decision=decision,
        approver_id=approver_id,
        reason=reason,
    )
    result["decision_id"] = decision_id
    return result


def get_approval_decision_state(*, store: EventStore, decision_id: str) -> dict[str, Any]:
    decision_events = [
        event
        for event in store.list_all()
        if event.payload.get("approval", {}).get("decision_id") == decision_id
    ]
    if not decision_events:
        raise ApprovalNotFoundError(event_id=decision_id, detail_path="decision_id")

    requested_event: StoredEvent | None = None
    resolved_event: StoredEvent | None = None
    for event in decision_events:
        if _is_pending_signal(event) and requested_event is None:
            requested_event = event
        if _is_resolution_signal(event):
            resolved_event = event

    anchor_event = resolved_event or requested_event or decision_events[-1]
    approval_payload = anchor_event.payload.get("approval", {})
    status = approval_payload.get("status")

    return {
        "decision_id": decision_id,
        "run_id": anchor_event.run_id,
        "status": status,
        "requested_event_id": requested_event.id if requested_event is not None else None,
        "resolved_event_id": resolved_event.id if resolved_event is not None else None,
        "requested_at": _format_timestamp(requested_event.timestamp) if requested_event is not None else None,
        "resolved_at": approval_payload.get("resolved_at"),
        "requested_by": (
            requested_event.payload.get("approval", {}).get("requested_by")
            if requested_event is not None
            else None
        ),
        "resolved_by": approval_payload.get("resolved_by"),
        "reason": approval_payload.get("reason"),
    }


def _append_resolution_event(
    *,
    store: EventStore,
    target_event: StoredEvent,
    run_events: list[StoredEvent],
    initial_run_status: str,
    decision: ApprovalDecision,
    approver_id: str,
    reason: str | None,
) -> dict[str, Any]:
    started_at = perf_counter()
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
            "decision_id": approval_data.get("decision_id"),
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

    orchestration_event_ids: list[str] = []
    if (
        decision == "approved"
        and target_event.run_id == _TRIAGE_INBOX_DEMO_RUN_ID
        and target_event.id == _TRIAGE_INBOX_DEMO_APPROVAL_EVENT_ID
    ):
        try:
            orchestration_event_ids = _append_triage_inbox_completion_events(
                store=store,
                run_id=target_event.run_id,
                resolved_at=stored.timestamp,
                confidence=target_event.payload.get("confidence"),
            )
        except StorageWriteError as exc:
            _append_triage_inbox_orchestration_error_event(
                store=store,
                run_id=target_event.run_id,
                resolved_at=stored.timestamp,
                details=str(exc),
            )
            raise
    run_events = store.list_by_run_id(target_event.run_id)
    projection = project_run_status(run_events)
    approval_to_state_update_ms = _elapsed_ms_ceiling(started_at, perf_counter())
    orchestration_receipt_gap_ms = _orchestration_receipt_gap_ms(
        run_events=run_events,
        resolution_event_id=stored.id,
        orchestration_event_ids=orchestration_event_ids,
    )

    return {
        "status": "resolved",
        "event_id": stored.id,
        "target_event_id": target_event.id,
        "run_id": target_event.run_id,
        "decision": decision,
        "resolved_at": resolved_at,
        "run_status": projection.status,
        "orchestration": {
            "applied": bool(orchestration_event_ids),
            "event_ids": orchestration_event_ids,
        },
        "timing": {
            "target_ms": _MVP_APPROVAL_TO_STATE_UPDATE_TARGET_MS,
            "approval_to_state_update_ms": approval_to_state_update_ms,
            "within_target": approval_to_state_update_ms <= _MVP_APPROVAL_TO_STATE_UPDATE_TARGET_MS,
            "orchestration_receipt_gap_ms": orchestration_receipt_gap_ms,
            "state_transition": f"{initial_run_status}->{projection.status}",
        },
    }


def _append_triage_inbox_completion_events(
    *,
    store: EventStore,
    run_id: str,
    resolved_at: datetime,
    confidence: Any,
) -> list[str]:
    resume_at = _format_timestamp(resolved_at + timedelta(milliseconds=1))
    complete_at = _format_timestamp(resolved_at + timedelta(milliseconds=2))

    resume_payload = validate_event_payload(
        {
            "id": "evt_triage_inbox_004",
            "run_id": run_id,
            "timestamp": resume_at,
            "type": "action",
            "actor": "agent",
            "title": "Resume triage_inbox after approval",
            "details": "Human approval received; sending final customer response.",
            "confidence": confidence,
            "risk_level": "medium",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [
                {
                    "kind": "log",
                    "label": "Post-approval execution log",
                    "ref": "log://triage-inbox/004",
                }
            ],
            "meta": {"workflow": "triage_inbox", "step": "resume_after_approval"},
        }
    )
    complete_payload = validate_event_payload(
        {
            "id": "evt_triage_inbox_005",
            "run_id": run_id,
            "timestamp": complete_at,
            "type": "summary",
            "actor": "agent",
            "title": "triage_inbox run completed",
            "details": "Workflow completed after human approval.",
            "confidence": confidence,
            "risk_level": "low",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [
                {
                    "kind": "artifact",
                    "label": "Final response receipt",
                    "ref": "artifact://triage-inbox/005",
                }
            ],
            "meta": {"workflow": "triage_inbox", "step": "run_completed"},
        }
    )

    try:
        store.append(resume_payload)
        store.append(complete_payload)
    except StorageWriteError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise StorageWriteError("triage_inbox orchestration append failed") from exc
    return [resume_payload.id, complete_payload.id]


def _append_triage_inbox_orchestration_error_event(
    *,
    store: EventStore,
    run_id: str,
    resolved_at: datetime,
    details: str,
) -> None:
    error_at = _format_timestamp(resolved_at + timedelta(milliseconds=3))
    error_event = validate_event_payload(
        {
            "id": f"evt_triage_inbox_err_{uuid4().hex[:10]}",
            "run_id": run_id,
            "timestamp": error_at,
            "type": "error",
            "actor": "system",
            "title": "triage_inbox orchestration failed",
            "details": f"Post-approval continuation failed: {details}",
            "confidence": None,
            "risk_level": "high",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [
                {
                    "kind": "log",
                    "label": "Orchestration failure log",
                    "ref": "log://triage-inbox/orchestration-error",
                }
            ],
            "meta": {"workflow": "triage_inbox", "step": "run_stopped"},
        }
    )
    try:
        store.append(error_event)
    except Exception:
        # Best effort journaling; preserve the original failure as the API error.
        return


def _orchestration_receipt_gap_ms(
    *,
    run_events: list[StoredEvent],
    resolution_event_id: str,
    orchestration_event_ids: list[str],
) -> int | None:
    if not orchestration_event_ids:
        return None

    timestamp_by_event_id = {event.id: event.timestamp for event in run_events}
    resolution_timestamp = timestamp_by_event_id.get(resolution_event_id)
    terminal_orchestration_timestamp = timestamp_by_event_id.get(orchestration_event_ids[-1])
    if resolution_timestamp is None or terminal_orchestration_timestamp is None:
        return None

    delta_ms = int((terminal_orchestration_timestamp - resolution_timestamp).total_seconds() * 1000)
    if delta_ms < 0:
        return None
    return delta_ms


def _elapsed_ms_ceiling(started_at: float, ended_at: float) -> int:
    elapsed = (ended_at - started_at) * 1000
    if elapsed <= 0:
        return 0
    return ceil(elapsed)


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


def _build_decision_pending_event_id(*, decision_id: str, timestamp: str) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").replace(".", "")
    compact_time = compact_time.replace("T", "T").replace("Z", "Z")
    return f"evt_{decision_id}_pending_{compact_time}_{uuid4().hex[:8]}"


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
