from typing import Any

from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    DuplicateApprovalError,
    DuplicateEventError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    RunNotFoundError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
)


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
                    "path": "event_id",
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
            "details": [
                {
                    "path": "event_id",
                    "message": str(exc),
                    "type": "state_conflict",
                    "code": "DUPLICATE_APPROVAL",
                }
            ],
        }
    }
