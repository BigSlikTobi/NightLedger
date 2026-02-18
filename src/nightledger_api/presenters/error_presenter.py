from typing import Any

from fastapi.exceptions import RequestValidationError

from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    BusinessRuleValidationError,
    DuplicateApprovalError,
    DuplicateEventError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    RunNotFoundError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
)


def present_business_rule_validation_error(exc: BusinessRuleValidationError) -> dict[str, Any]:
    return {
        "error": {
            "code": "BUSINESS_RULE_VIOLATION",
            "message": "Event payload violates workflow governance rules",
            "details": [
                {
                    "path": detail.path,
                    "message": detail.message,
                    "type": detail.type,
                    "code": detail.code,
                    "rule_id": detail.rule_id,
                }
                for detail in exc.details
            ],
        }
    }


def present_schema_validation_error(exc: SchemaValidationError) -> dict[str, Any]:
    return {
        "error": {
            "code": "SCHEMA_VALIDATION_ERROR",
            "message": "Event payload failed schema validation",
            "details": [
                {
                    "path": detail.path,
                    "message": detail.message,
                    "type": detail.type,
                    "code": detail.code,
                }
                for detail in exc.details
            ],
        }
    }


def present_storage_write_error(exc: StorageWriteError) -> dict[str, Any]:
    return {
        "error": {
            "code": "STORAGE_WRITE_ERROR",
            "message": "Failed to persist event",
            "details": [
                {
                    "path": "storage",
                    "message": str(exc),
                    "type": "storage_failure",
                    "code": "STORAGE_APPEND_FAILED",
                }
            ],
        }
    }


def present_storage_read_error(exc: StorageReadError) -> dict[str, Any]:
    return {
        "error": {
            "code": "STORAGE_READ_ERROR",
            "message": "Failed to load events",
            "details": [
                {
                    "path": "storage",
                    "message": str(exc),
                    "type": "storage_failure",
                    "code": "STORAGE_READ_FAILED",
                }
            ],
        }
    }


def present_duplicate_event_error(exc: DuplicateEventError) -> dict[str, Any]:
    return {
        "error": {
            "code": "DUPLICATE_EVENT_ID",
            "message": "Event ID already exists for this run",
            "details": [
                {
                    "path": "event_id",
                    "message": str(exc),
                    "type": "duplicate_event",
                    "code": "DUPLICATE_EVENT_ID",
                }
            ],
        }
    }


def present_run_not_found_error(exc: RunNotFoundError) -> dict[str, Any]:
    return {
        "error": {
            "code": "RUN_NOT_FOUND",
            "message": "Run not found",
            "details": [
                {
                    "path": "run_id",
                    "message": str(exc),
                    "type": "not_found",
                    "code": "RUN_NOT_FOUND",
                }
            ],
        }
    }


def present_inconsistent_run_state_error(exc: InconsistentRunStateError) -> dict[str, Any]:
    return {
        "error": {
            "code": "INCONSISTENT_RUN_STATE",
            "message": "Run events contain inconsistent approval state",
            "details": [
                {
                    "path": exc.detail_path,
                    "message": exc.detail_message,
                    "type": exc.detail_type,
                    "code": exc.detail_code,
                }
            ],
        }
    }


def present_approval_not_found_error(exc: ApprovalNotFoundError) -> dict[str, Any]:
    return {
        "error": {
            "code": "APPROVAL_NOT_FOUND",
            "message": "Approval target not found",
            "details": [
                {
                    "path": exc.detail_path,
                    "message": str(exc),
                    "type": "not_found",
                    "code": "APPROVAL_NOT_FOUND",
                }
            ],
        }
    }


def present_ambiguous_event_id_error(exc: AmbiguousEventIdError) -> dict[str, Any]:
    return {
        "error": {
            "code": "AMBIGUOUS_EVENT_ID",
            "message": "Event ID maps to multiple runs",
            "details": [
                {
                    "path": "event_id",
                    "message": str(exc),
                    "type": "state_conflict",
                    "code": "AMBIGUOUS_EVENT_ID",
                }
            ],
        }
    }


def present_no_pending_approval_error(exc: NoPendingApprovalError) -> dict[str, Any]:
    return {
        "error": {
            "code": "NO_PENDING_APPROVAL",
            "message": "No pending approval for target event",
            "rule_ids": ["RULE-GATE-002"],
            "details": [
                {
                    "path": "event_id",
                    "message": str(exc),
                    "type": "state_conflict",
                    "code": "NO_PENDING_APPROVAL",
                }
            ],
        }
    }


def present_duplicate_approval_error(exc: DuplicateApprovalError) -> dict[str, Any]:
    return {
        "error": {
            "code": "DUPLICATE_APPROVAL",
            "message": "Approval already resolved",
            "rule_ids": ["RULE-GATE-003"],
            "details": [
                {
                    "path": exc.detail_path,
                    "message": str(exc),
                    "type": "state_conflict",
                    "code": "DUPLICATE_APPROVAL",
                }
            ],
        }
    }


def present_approval_request_validation_error(
    exc: RequestValidationError,
) -> dict[str, Any]:
    details: list[dict[str, str]] = []
    rule_ids: set[str] = set()

    for error in exc.errors():
        loc = error.get("loc", ())
        if len(loc) < 2 or loc[0] != "body":
            continue

        path = ".".join(str(part) for part in loc[1:])
        details.append(
            {
                "path": path,
                "message": str(error.get("msg", "Invalid input")),
                "type": str(error.get("type", "validation_error")),
                "code": _map_approval_validation_code(
                    path=path,
                    error_type=str(error.get("type", "validation_error")),
                ),
            }
        )
        rule_id = _map_approval_rule_id(details[-1]["code"])
        if rule_id is not None:
            rule_ids.add(rule_id)

    details.sort(key=lambda detail: (detail["path"], detail["code"], detail["type"]))

    return {
        "error": {
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "Approval request payload failed validation",
            "rule_ids": sorted(rule_ids),
            "details": details,
        }
    }


def present_authorize_action_request_validation_error(
    exc: RequestValidationError,
) -> dict[str, Any]:
    return present_authorize_action_validation_errors(exc.errors())


def present_authorize_action_validation_errors(
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    details: list[dict[str, str]] = []

    for error in errors:
        loc = error.get("loc", ())
        if len(loc) < 1:
            continue

        start_index = 1 if str(loc[0]) == "body" else 0
        path = ".".join(str(part) for part in loc[start_index:])
        details.append(
            {
                "path": path,
                "message": str(error.get("msg", "Invalid input")),
                "type": str(error.get("type", "validation_error")),
                "code": _map_authorize_action_validation_code(
                    path=path,
                    error_type=str(error.get("type", "validation_error")),
                ),
            }
        )

    details.sort(key=lambda detail: (detail["path"], detail["code"], detail["type"]))

    return {
        "error": {
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "authorize_action payload failed validation",
            "details": details,
        }
    }


def _map_approval_validation_code(*, path: str, error_type: str) -> str:
    if path == "decision":
        if error_type == "missing":
            return "MISSING_APPROVAL_DECISION"
        return "INVALID_APPROVAL_DECISION"

    if path == "approver_id":
        if error_type in {"missing", "string_too_short"}:
            return "MISSING_APPROVER_ID"
        return "INVALID_APPROVER_ID"

    return "REQUEST_VALIDATION_ERROR"


def _map_approval_rule_id(detail_code: str) -> str | None:
    mapping = {
        "MISSING_APPROVAL_DECISION": "RULE-GATE-004",
        "INVALID_APPROVAL_DECISION": "RULE-GATE-004",
        "MISSING_APPROVER_ID": "RULE-GATE-007",
    }
    return mapping.get(detail_code)


def _map_authorize_action_validation_code(*, path: str, error_type: str) -> str:
    if path == "intent":
        if error_type == "missing":
            return "MISSING_INTENT"
        return "INVALID_INTENT"
    if path == "context":
        if error_type == "missing":
            return "MISSING_CONTEXT"
        return "INVALID_CONTEXT"
    if path == "intent.action":
        if error_type == "missing":
            return "MISSING_ACTION"
        return "UNSUPPORTED_ACTION"
    if path == "context.amount":
        if error_type == "missing":
            return "MISSING_AMOUNT"
        return "INVALID_AMOUNT"
    if path == "context.currency":
        if error_type == "missing":
            return "MISSING_CURRENCY"
        return "UNSUPPORTED_CURRENCY"
    if path == "context.transport_decision_hint":
        if error_type == "missing":
            return "MISSING_TRANSPORT_DECISION_HINT"
        return "INVALID_TRANSPORT_DECISION_HINT"
    return "REQUEST_VALIDATION_ERROR"
