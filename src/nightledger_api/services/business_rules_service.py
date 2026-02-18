from nightledger_api.models.event_schema import EventPayload
from nightledger_api.services.errors import (
    BusinessRuleValidationError,
    BusinessRuleViolationDetail,
    InconsistentRunStateError,
)
from nightledger_api.services.event_store import StoredEvent
from nightledger_api.services.run_status_service import project_run_status

_TERMINAL_RUN_STATUSES = {"completed", "stopped", "expired"}
_TERMINAL_STEP_STATUS: dict[str, str] = {
    "run_expired": "expired",
    "approval_expired": "expired",
    "run_stopped": "stopped",
    "approval_rejected": "stopped",
}


def validate_event_business_rules(
    *,
    event: EventPayload,
    existing_events: list[StoredEvent],
) -> None:
    violations: list[BusinessRuleViolationDetail] = []
    existing_projection = None

    if existing_events:
        terminal_status = _terminal_status_from_event_payload(existing_events[-1].payload)
        if terminal_status in _TERMINAL_RUN_STATUSES:
            violations.append(
                BusinessRuleViolationDetail(
                    path="workflow_status",
                    message=(
                        "event stream continued after terminal status "
                        f"'{terminal_status}'"
                    ),
                    type="state_conflict",
                    code="TERMINAL_STATE_CONFLICT",
                    rule_id="RULE-GATE-005",
                )
            )

    if event.type == "approval_requested":
        if not event.requires_approval:
            violations.append(
                BusinessRuleViolationDetail(
                    path="requires_approval",
                    message="approval_requested must set requires_approval=true",
                    type="state_conflict",
                    code="INVALID_APPROVAL_TRANSITION",
                    rule_id="RULE-GATE-001",
                )
            )
        if event.approval.status != "pending":
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval.status",
                    message="approval_requested must use approval.status='pending'",
                    type="state_conflict",
                    code="INVALID_APPROVAL_TRANSITION",
                    rule_id="RULE-GATE-001",
                )
            )

    if event.type == "approval_resolved":
        projection = (
            existing_projection
            if existing_projection is not None
            else _project_existing_run_status(existing_events)
        )
        pending_approval = projection.pending_approval if projection is not None else None
        if pending_approval is None:
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval",
                    message="approval_resolved encountered without pending approval",
                    type="state_conflict",
                    code="NO_PENDING_APPROVAL",
                    rule_id="RULE-GATE-002",
                )
            )
        else:
            pending_event_id = pending_approval.get("event_id")
            pending_event = _find_event_by_id(existing_events, pending_event_id)
            pending_decision_id = (
                pending_event.payload.get("approval", {}).get("decision_id")
                if pending_event is not None
                else None
            )
            if pending_decision_id is not None and event.approval.decision_id != pending_decision_id:
                violations.append(
                    BusinessRuleViolationDetail(
                        path="approval.decision_id",
                        message=(
                            "approval_resolved decision_id does not match active "
                            "pending approval"
                        ),
                        type="state_conflict",
                        code="APPROVAL_DECISION_ID_MISMATCH",
                        rule_id="RULE-GATE-004",
                    )
                )
        resolved_by = event.approval.resolved_by
        if resolved_by is None or (isinstance(resolved_by, str) and not resolved_by.strip()):
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval.resolved_by",
                    message="approval_resolved is missing approver identity",
                    type="state_conflict",
                    code="MISSING_APPROVER_ID",
                    rule_id="RULE-GATE-007",
                )
            )
        resolved_at = event.approval.resolved_at
        if resolved_at is None:
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval.resolved_at",
                    message="approval_resolved is missing resolution timestamp",
                    type="state_conflict",
                    code="MISSING_APPROVAL_TIMESTAMP",
                    rule_id="RULE-GATE-008",
                )
            )

    if event.type == "summary":
        if event.requires_approval:
            violations.append(
                BusinessRuleViolationDetail(
                    path="requires_approval",
                    message="summary events must set requires_approval=false",
                    type="state_conflict",
                    code="INVALID_SUMMARY_COMPLETION",
                    rule_id="RULE-GATE-010",
                )
            )
        if event.approval.status != "not_required":
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval.status",
                    message="summary events must use approval.status='not_required'",
                    type="state_conflict",
                    code="INVALID_SUMMARY_COMPLETION",
                    rule_id="RULE-GATE-010",
                )
            )
        projection = (
            existing_projection
            if existing_projection is not None
            else _project_existing_run_status(existing_events)
        )
        if projection is not None and projection.pending_approval is not None:
            violations.append(
                BusinessRuleViolationDetail(
                    path="approval",
                    message="summary cannot complete a run while approval is still pending",
                    type="state_conflict",
                    code="PENDING_APPROVAL_EXISTS",
                    rule_id="RULE-GATE-010",
                )
            )

    if event.type == "action" and (event.risk_level == "high" or event.requires_approval):
        if len(event.evidence) == 0:
            violations.append(
                BusinessRuleViolationDetail(
                    path="evidence",
                    message="risky action events must include at least one evidence item",
                    type="state_conflict",
                    code="MISSING_RISK_EVIDENCE",
                    rule_id="RULE-RISK-005",
                )
            )

    if violations:
        raise BusinessRuleValidationError(violations)


def _project_existing_run_status(existing_events: list[StoredEvent]):
    if not existing_events:
        return None
    try:
        return project_run_status(existing_events)
    except InconsistentRunStateError as exc:
        raise BusinessRuleValidationError(
            [
                BusinessRuleViolationDetail(
                    path=exc.detail_path,
                    message=exc.detail_message,
                    type=exc.detail_type,
                    code=exc.detail_code,
                    rule_id=_rule_id_for_code(exc.detail_code),
                )
            ]
        ) from exc


def _rule_id_for_code(code: str) -> str:
    mapping = {
        "NO_PENDING_APPROVAL": "RULE-GATE-002",
        "DUPLICATE_PENDING_APPROVAL": "RULE-GATE-001",
        "INVALID_APPROVAL_TRANSITION": "RULE-GATE-004",
        "MISSING_APPROVER_ID": "RULE-GATE-007",
        "MISSING_APPROVAL_TIMESTAMP": "RULE-GATE-008",
        "TERMINAL_STATE_CONFLICT": "RULE-GATE-005",
    }
    return mapping.get(code, "RULE-GATE-002")


def _terminal_status_from_event_payload(payload: dict[str, object]) -> str | None:
    event_type = payload.get("type")
    if event_type == "summary":
        return "completed"

    meta = payload.get("meta")
    if isinstance(meta, dict):
        step = meta.get("step")
        if isinstance(step, str):
            return _TERMINAL_STEP_STATUS.get(step)

    return None


def _find_event_by_id(events: list[StoredEvent], event_id: str | None) -> StoredEvent | None:
    if event_id is None:
        return None
    for event in events:
        if event.id == event_id:
            return event
    return None
