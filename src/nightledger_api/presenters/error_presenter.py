from typing import Any

from nightledger_api.services.errors import SchemaValidationError


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
