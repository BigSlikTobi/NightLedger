from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationDetail:
    path: str
    message: str
    type: str
    code: str


@dataclass(frozen=True)
class BusinessRuleViolationDetail:
    path: str
    message: str
    type: str
    code: str
    rule_id: str


class SchemaValidationError(Exception):
    def __init__(self, details: list[ValidationDetail]) -> None:
        super().__init__("Event payload failed schema validation")
        self.details = details


class BusinessRuleValidationError(Exception):
    def __init__(self, details: list[BusinessRuleViolationDetail]) -> None:
        super().__init__("Event payload violates workflow governance rules")
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


class RunNotFoundError(Exception):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"No events found for run '{run_id}'")


class InconsistentRunStateError(Exception):
    def __init__(
        self,
        *,
        detail_path: str,
        detail_message: str,
        detail_code: str,
        detail_type: str = "state_conflict",
    ) -> None:
        self.detail_path = detail_path
        self.detail_message = detail_message
        self.detail_code = detail_code
        self.detail_type = detail_type
        super().__init__(detail_message)


class ApprovalNotFoundError(Exception):
    def __init__(self, event_id: str, *, detail_path: str = "event_id") -> None:
        self.event_id = event_id
        self.detail_path = detail_path
        if detail_path == "decision_id":
            super().__init__(f"Approval decision '{event_id}' was not found")
        else:
            super().__init__(f"Approval target event '{event_id}' was not found")


class AmbiguousEventIdError(Exception):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event ID '{event_id}' exists in multiple runs")


class NoPendingApprovalError(Exception):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Event '{event_id}' is not the currently pending approval")


class DuplicateApprovalError(Exception):
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(f"Approval for event '{event_id}' has already been resolved")
