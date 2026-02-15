from typing import Any

from pydantic import ValidationError

from nightledger_api.models.event_schema import EventPayload
from nightledger_api.services.errors import SchemaValidationError, ValidationDetail


def validate_event_payload(payload: dict[str, Any]) -> EventPayload:
    try:
        return EventPayload.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(_map_validation_details(exc)) from exc


def _map_validation_details(exc: ValidationError) -> list[ValidationDetail]:
    details: list[ValidationDetail] = []
    for error in exc.errors():
        path = ".".join(str(part) for part in error["loc"])
        details.append(
            ValidationDetail(
                path=path,
                message=error["msg"],
                type=error["type"],
                code=_map_rule_code(path=path, error_type=error["type"]),
            )
        )
    return sorted(details, key=lambda detail: detail.path)


def _map_rule_code(path: str, error_type: str) -> str:
    if error_type == "missing":
        return _missing_field_code(path)

    if error_type == "extra_forbidden":
        return "UNKNOWN_FIELD"

    if path == "timestamp" and error_type in {"value_error", "datetime_parsing", "datetime_from_date_parsing"}:
        return "INVALID_TIMESTAMP"

    if path == "confidence" and error_type in {"greater_than_equal", "less_than_equal"}:
        return "INVALID_CONFIDENCE_BOUNDS"

    if path == "confidence" and error_type == "float_parsing":
        return "INVALID_CONFIDENCE_TYPE"

    if path in {"title", "details"} and error_type in {"string_too_short", "missing"}:
        return "MISSING_TIMELINE_FIELDS"
    
    if path == "run_id" and error_type == "string_too_short":
        return "MISSING_RUN_ID"

    if error_type == "literal_error":
        return _literal_error_code(path)

    return "SCHEMA_VALIDATION_ERROR"


def _missing_field_code(path: str) -> str:
    mapping = {
        "id": "MISSING_EVENT_ID",
        "run_id": "MISSING_RUN_ID",
        "timestamp": "MISSING_TIMESTAMP",
        "type": "MISSING_EVENT_TYPE",
        "actor": "MISSING_ACTOR",
        "title": "MISSING_TIMELINE_FIELDS",
        "details": "MISSING_TIMELINE_FIELDS",
        "approval": "MISSING_APPROVAL",
    }
    return mapping.get(path, "MISSING_REQUIRED_FIELD")


def _literal_error_code(path: str) -> str:
    if path == "type":
        return "INVALID_EVENT_TYPE"
    if path == "actor":
        return "INVALID_ACTOR"
    if path == "risk_level":
        return "INVALID_RISK_LEVEL"
    if path == "approval.status":
        return "INVALID_APPROVAL_STATUS"
    if path.endswith(".kind"):
        return "INVALID_EVIDENCE_KIND"
    return "INVALID_ENUM_VALUE"
