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
    ExecutionActionMismatchError,
    ExecutionDecisionNotApprovedError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
    ExecutionTokenMisconfiguredError,
    ExecutionTokenMissingError,
    ExecutionTokenReplayedError,
    ExecutionPayloadMismatchError,
    RuleConfigurationError,
    RuleExpressionError,
    RuleInputError,
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
    message = "Approval already resolved"
    if exc.reason == "pending":
        message = "Approval already pending"
    elif exc.reason == "exists":
        message = "Approval already exists"
    return {
        "error": {
            "code": "DUPLICATE_APPROVAL",
            "message": message,
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


def present_execution_token_missing_error(exc: ExecutionTokenMissingError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_TOKEN_MISSING",
            "message": str(exc),
            "details": [
                {
                    "path": "authorization",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_TOKEN_MISSING",
                }
            ],
        }
    }


def present_execution_token_invalid_error(exc: ExecutionTokenInvalidError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_TOKEN_INVALID",
            "message": str(exc),
            "details": [
                {
                    "path": "authorization",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_TOKEN_INVALID",
                }
            ],
        }
    }


def present_execution_token_expired_error(exc: ExecutionTokenExpiredError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_TOKEN_EXPIRED",
            "message": str(exc),
            "details": [
                {
                    "path": "authorization",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_TOKEN_EXPIRED",
                }
            ],
        }
    }


def present_execution_token_replayed_error(exc: ExecutionTokenReplayedError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_TOKEN_REPLAYED",
            "message": str(exc),
            "details": [
                {
                    "path": "authorization",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_TOKEN_REPLAYED",
                }
            ],
        }
    }


def present_execution_action_mismatch_error(exc: ExecutionActionMismatchError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_ACTION_MISMATCH",
            "message": str(exc),
            "details": [
                {
                    "path": "authorization",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_ACTION_MISMATCH",
                }
            ],
        }
    }


def present_execution_decision_not_approved_error(
    exc: ExecutionDecisionNotApprovedError,
) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_DECISION_NOT_APPROVED",
            "message": str(exc),
            "details": [
                {
                    "path": "decision_id",
                    "message": str(exc),
                    "type": "state_conflict",
                    "code": "EXECUTION_DECISION_NOT_APPROVED",
                }
            ],
        }
    }


def present_execution_payload_mismatch_error(exc: ExecutionPayloadMismatchError) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_PAYLOAD_MISMATCH",
            "message": str(exc),
            "details": [
                {
                    "path": "payload",
                    "message": str(exc),
                    "type": "auth_error",
                    "code": "EXECUTION_PAYLOAD_MISMATCH",
                }
            ],
        }
    }


def present_execution_token_misconfigured_error(
    exc: ExecutionTokenMisconfiguredError,
) -> dict[str, Any]:
    return {
        "error": {
            "code": "EXECUTION_TOKEN_MISCONFIGURED",
            "message": str(exc),
            "details": [
                {
                    "path": "configuration",
                    "message": str(exc),
                    "type": "configuration_error",
                    "code": "EXECUTION_TOKEN_MISCONFIGURED",
                }
            ],
        }
    }


def present_rule_configuration_error(exc: RuleConfigurationError) -> dict[str, Any]:
    return {
        "error": {
            "code": "RULE_CONFIGURATION_ERROR",
            "message": str(exc),
            "details": [
                {
                    "path": "configuration",
                    "message": str(exc),
                    "type": "configuration_error",
                    "code": "RULE_CONFIGURATION_ERROR",
                }
            ],
        }
    }


def present_rule_expression_error(exc: RuleExpressionError) -> dict[str, Any]:
    return {
        "error": {
            "code": "RULE_EXPRESSION_INVALID",
            "message": str(exc),
            "details": [
                {
                    "path": "rule.when",
                    "message": str(exc),
                    "type": "configuration_error",
                    "code": "RULE_EXPRESSION_INVALID",
                    "rule_id": exc.rule_id,
                    "expression": exc.expression,
                }
            ],
        }
    }


def present_rule_input_error(exc: RuleInputError) -> dict[str, Any]:
    return {
        "error": {
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "authorize_action payload failed validation",
            "details": [
                {
                    "path": exc.path,
                    "message": str(exc),
                    "type": "missing",
                    "code": "MISSING_RULE_INPUT",
                }
            ],
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
        return "INVALID_ACTION"
    if path == "context.user_id":
        if error_type in {"missing", "string_too_short"}:
            return "MISSING_USER_ID"
        return "INVALID_USER_ID"
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
