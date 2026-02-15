from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from nightledger_api.services.errors import InconsistentRunStateError
from nightledger_api.services.event_store import StoredEvent

RunWorkflowStatus = Literal[
    "running",
    "paused",
    "approved",
    "rejected",
    "stopped",
    "expired",
    "completed",
]

_TERMINAL_STEP_STATUS: dict[str, RunWorkflowStatus] = {
    "run_expired": "expired",
    "approval_expired": "expired",
    "run_stopped": "stopped",
    "approval_rejected": "stopped",
}


@dataclass(frozen=True)
class PendingApprovalContext:
    event_id: str
    requested_by: str | None
    requested_at: str
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RunStatusProjection:
    status: RunWorkflowStatus
    pending_approval: dict[str, Any] | None


def project_run_status(events: list[StoredEvent]) -> RunStatusProjection:
    status: RunWorkflowStatus = "running"
    pending_approval: PendingApprovalContext | None = None
    terminal_status: RunWorkflowStatus | None = None

    for event in events:
        payload = event.payload
        event_type = str(payload.get("type", ""))
        approval = payload.get("approval", {})
        approval_status = str(approval.get("status", ""))
        requires_approval = bool(payload.get("requires_approval", False))

        if terminal_status is not None:
            raise InconsistentRunStateError(
                detail_path="workflow_status",
                detail_message=(
                    f"event stream continued after terminal status '{terminal_status}'"
                ),
                detail_code="TERMINAL_STATE_CONFLICT",
                detail_type="state_conflict",
            )

        next_terminal_status = _to_terminal_status(payload)
        if status == "rejected" and next_terminal_status is None:
            raise InconsistentRunStateError(
                detail_path="workflow_status",
                detail_message="event stream continued after rejection without terminal stop",
                detail_code="REJECTED_STATE_CONFLICT",
                detail_type="state_conflict",
            )

        if next_terminal_status is not None:
            terminal_status = next_terminal_status
            status = next_terminal_status
            pending_approval = None
            continue

        if _is_resolution_signal(
            event_type=event_type,
            approval_status=approval_status,
            requires_approval=requires_approval,
        ):
            if approval_status not in {"approved", "rejected"}:
                raise InconsistentRunStateError(
                    detail_path="approval.status",
                    detail_message="approval_resolved must use approved or rejected status",
                    detail_code="INVALID_APPROVAL_TRANSITION",
                    detail_type="state_conflict",
                )
            if pending_approval is None:
                raise InconsistentRunStateError(
                    detail_path="approval",
                    detail_message="approval_resolved encountered without pending approval",
                    detail_code="NO_PENDING_APPROVAL",
                    detail_type="state_conflict",
                )
            resolved_by = approval.get("resolved_by")
            if resolved_by is None or (isinstance(resolved_by, str) and not resolved_by.strip()):
                raise InconsistentRunStateError(
                    detail_path="approval.resolved_by",
                    detail_message="approval_resolved is missing approver identity",
                    detail_code="MISSING_APPROVER_ID",
                    detail_type="state_conflict",
                )
            resolved_at = approval.get("resolved_at")
            if resolved_at is None or (isinstance(resolved_at, str) and not resolved_at.strip()):
                raise InconsistentRunStateError(
                    detail_path="approval.resolved_at",
                    detail_message="approval_resolved is missing resolution timestamp",
                    detail_code="MISSING_APPROVAL_TIMESTAMP",
                    detail_type="state_conflict",
                )
            pending_approval = None
            status = "approved" if approval_status == "approved" else "rejected"
            continue

        if _is_pending_signal(
            event_type=event_type,
            approval_status=approval_status,
            requires_approval=requires_approval,
        ):
            if pending_approval is not None:
                raise InconsistentRunStateError(
                    detail_path="approval",
                    detail_message="multiple pending approvals encountered without resolution",
                    detail_code="DUPLICATE_PENDING_APPROVAL",
                    detail_type="state_conflict",
                )
            pending_approval = _pending_context_from_event(event)
            status = "paused"
            continue

        if pending_approval is not None:
            status = "paused"
            continue

        if status == "approved":
            status = "running"

    return RunStatusProjection(
        status=status,
        pending_approval=pending_approval.to_dict() if pending_approval is not None else None,
    )


def _is_pending_signal(
    *, event_type: str, approval_status: str, requires_approval: bool
) -> bool:
    return event_type == "approval_requested" or (
        requires_approval and approval_status == "pending"
    )


def _is_resolution_signal(
    *, event_type: str, approval_status: str, requires_approval: bool
) -> bool:
    if event_type == "approval_resolved":
        return True
    return requires_approval and approval_status in {"approved", "rejected"}


def _pending_context_from_event(event: StoredEvent) -> PendingApprovalContext:
    approval = event.payload.get("approval", {})
    details = event.payload.get("details")
    fallback_reason = details if isinstance(details, str) else None
    reason = approval.get("reason") or fallback_reason

    requested_by = approval.get("requested_by")
    if requested_by is not None and not isinstance(requested_by, str):
        requested_by = str(requested_by)

    return PendingApprovalContext(
        event_id=event.id,
        requested_by=requested_by,
        requested_at=_format_timestamp(event.timestamp),
        reason=reason if isinstance(reason, str) else None,
    )


def _to_terminal_status(payload: dict[str, Any]) -> RunWorkflowStatus | None:
    event_type = payload.get("type")
    if event_type == "summary":
        return "completed"

    meta = payload.get("meta")
    if isinstance(meta, dict):
        step = meta.get("step")
        if isinstance(step, str):
            return _TERMINAL_STEP_STATUS.get(step)

    return None


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
