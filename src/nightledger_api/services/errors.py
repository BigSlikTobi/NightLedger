from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationDetail:
    path: str
    message: str
    type: str
    code: str


class SchemaValidationError(Exception):
    def __init__(self, details: list[ValidationDetail]) -> None:
        super().__init__("Event payload failed schema validation")
        self.details = details
