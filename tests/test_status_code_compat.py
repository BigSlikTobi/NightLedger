from pathlib import Path
import sys

from fastapi import status

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api import main  # noqa: E402


def test_schema_validation_status_code_supports_starlette_compatibility() -> None:
    if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
        expected = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        expected = getattr(status, "HTTP_422_UNPROCESSABLE_ENTITY", 422)
    assert main.SCHEMA_VALIDATION_STATUS_CODE == expected
