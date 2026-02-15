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


class StorageWriteError(Exception):
    pass


class StorageReadError(Exception):
    pass


class DuplicateEventError(Exception):
    """Raised when attempting to append an event with duplicate event_id within a run_id."""
    
    def __init__(self, event_id: str, run_id: str) -> None:
        self.event_id = event_id
        self.run_id = run_id
        super().__init__(f"Event ID '{event_id}' already exists for run '{run_id}'")

