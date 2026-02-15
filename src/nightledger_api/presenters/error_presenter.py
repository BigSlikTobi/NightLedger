from typing import Any

from nightledger_api.services.errors import (
    DuplicateEventError,
    InconsistentRunStateError,
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
