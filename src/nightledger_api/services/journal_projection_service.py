from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from nightledger_api.services.errors import InconsistentRunStateError
from nightledger_api.services.event_store import StoredEvent


@dataclass(frozen=True)
class PayloadRef:
    run_id: str
    event_id: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "event_id": self.event_id,
            "path": self.path,
        }


@dataclass(frozen=True)
class ApprovalContext:
    requires_approval: bool
    status: str
    requested_by: str | None
    resolved_by: str | None
    resolved_at: str | None
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requires_approval": self.requires_approval,
            "status": self.status,
            "requested_by": self.requested_by,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class JournalEntry:
    entry_id: str
    event_id: str
    timestamp: str
    event_type: str
    title: str
    details: str
    payload_ref: PayloadRef
    approval_context: ApprovalContext
    metadata: dict[str, Any]
    evidence_refs: list[dict[str, str]]
    approval_indicator: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "entry_id": self.entry_id,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "title": self.title,
            "details": self.details,
            "payload_ref": self.payload_ref.to_dict(),
            "approval_context": self.approval_context.to_dict(),
            "metadata": self.metadata,
        }
        if self.evidence_refs:
            body["evidence_refs"] = self.evidence_refs
        if self.approval_indicator is not None:
            body["approval_indicator"] = self.approval_indicator
        return body


@dataclass(frozen=True)
class RunJournalProjection:
    run_id: str
    entries: list[JournalEntry]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def project_run_journal(*, run_id: str, events: list[StoredEvent]) -> RunJournalProjection:
    entries: list[JournalEntry] = []

    for index, event in enumerate(events, start=1):
        if event.run_id != run_id:
            raise InconsistentRunStateError(
                detail_path="run_id",
                detail_message=(
                    f"event '{event.id}' belongs to run '{event.run_id}', expected '{run_id}'"
                ),
                detail_code="CROSS_RUN_EVENT_STREAM",
                detail_type="state_conflict",
            )

        payload = event.payload
        approval = payload.get("approval", {})

        entries.append(
            JournalEntry(
                entry_id=f"jrnl_{run_id}_{index:04d}",
                event_id=event.id,
                timestamp=_format_timestamp(event.timestamp),
                event_type=_string(payload.get("type")),
                title=_string(payload.get("title")),
                details=_string(payload.get("details")),
                payload_ref=PayloadRef(
                    run_id=run_id,
                    event_id=event.id,
                    path=f"/v1/runs/{run_id}/events#{event.id}",
                ),
                approval_context=ApprovalContext(
                    requires_approval=bool(payload.get("requires_approval", False)),
                    status=_approval_status(approval),
                    requested_by=_optional_string(approval.get("requested_by")),
                    resolved_by=_optional_string(approval.get("resolved_by")),
                    resolved_at=_optional_timestamp_string(approval.get("resolved_at")),
                    reason=_optional_string(approval.get("reason")),
                ),
                metadata={
                    "actor": _string(payload.get("actor")),
                    "confidence": payload.get("confidence"),
                    "risk_level": _optional_string(payload.get("risk_level")),
                    "integrity_warning": event.integrity_warning,
                },
                evidence_refs=_evidence_refs(payload.get("evidence")),
                approval_indicator=_approval_indicator(payload, approval),
            )
        )

    return RunJournalProjection(run_id=run_id, entries=entries)


def _string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value) if value is not None else ""


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _approval_status(approval: Any) -> str:
    if not isinstance(approval, dict):
        return "not_required"
    status = approval.get("status")
    if isinstance(status, str):
        return status
    return "not_required"


def _optional_timestamp_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _format_timestamp(value)
    if isinstance(value, str):
        return value
    return str(value)


def _evidence_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    refs: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "kind": _string(item.get("kind")),
                "label": _string(item.get("label")),
                "ref": _string(item.get("ref")),
            }
        )
    return refs


def _approval_indicator(payload: dict[str, Any], approval: Any) -> dict[str, Any] | None:
    approval_status = _approval_status(approval)
    event_type = _string(payload.get("type"))
    is_approval_required = bool(payload.get("requires_approval", False)) or (
        event_type == "approval_requested"
    )
    is_approval_resolved = event_type == "approval_resolved" or (
        approval_status in {"approved", "rejected"}
    )

    if not is_approval_required and not is_approval_resolved:
        return None

    return {
        "is_approval_required": is_approval_required,
        "is_approval_resolved": is_approval_resolved,
        "decision": approval_status if is_approval_resolved else None,
    }


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
