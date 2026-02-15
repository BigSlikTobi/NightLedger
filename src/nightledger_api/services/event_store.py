from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from nightledger_api.models.event_schema import EventPayload
from nightledger_api.services.errors import DuplicateEventError


@dataclass(frozen=True)
class StoredEvent:
    id: str
    timestamp: datetime
    run_id: str
    payload: dict[str, Any]
    integrity_warning: bool = False


class EventStore(Protocol):
    def append(self, event: EventPayload) -> StoredEvent:
        """Append an event to the store.

        Raises:
            DuplicateEventError: If event.id already exists for event.run_id.
        """
        raise NotImplementedError

    def list_by_run_id(self, run_id: str) -> list[StoredEvent]:
        """List all events for a given run_id, ordered by timestamp (ascending).
        
        Returns an empty list if the run_id has no events.
        Events with identical timestamps are ordered by their insertion sequence.
        """
        raise NotImplementedError

    def list_all(self) -> list[StoredEvent]:
        """List all events across runs, ordered by timestamp (ascending)."""
        raise NotImplementedError


@dataclass(frozen=True)
class _StoredRecord:
    sequence: int
    id: str
    timestamp: datetime
    run_id: str
    payload: dict[str, Any]
    integrity_warning: bool = False


class InMemoryAppendOnlyEventStore:
    def __init__(self) -> None:
        self._sequence = 0
        self._event_id_index: dict[str, set[str]] = defaultdict(set)
        self._run_records_index: dict[str, list[_StoredRecord]] = defaultdict(list)
        self._last_timestamp_by_run: dict[str, datetime] = {}

    def append(self, event: EventPayload) -> StoredEvent:
        # RULE-CORE-003: Duplicate Event Prevention (O(1) lookup)
        if event.id in self._event_id_index[event.run_id]:
            raise DuplicateEventError(event_id=event.id, run_id=event.run_id)

        # RULE-CORE-005: Out-of-order timestamp detection (O(1) lookup)
        integrity_warning = False
        if event.run_id in self._last_timestamp_by_run:
            if event.timestamp < self._last_timestamp_by_run[event.run_id]:
                integrity_warning = True
            else:
                # Update last timestamp only if this event is newer
                self._last_timestamp_by_run[event.run_id] = event.timestamp
        else:
            # First event for this run
            self._last_timestamp_by_run[event.run_id] = event.timestamp

        self._sequence += 1
        record = _StoredRecord(
            sequence=self._sequence,
            id=event.id,
            timestamp=event.timestamp,
            run_id=event.run_id,
            payload=event.model_dump(mode="json"),
            integrity_warning=integrity_warning,
        )
        self._event_id_index[event.run_id].add(event.id)
        self._run_records_index[event.run_id].append(record)
        return self._to_stored_event(record)

    def list_by_run_id(self, run_id: str) -> list[StoredEvent]:
        # O(1) lookup via index, then O(k log k) sort where k = events in this run
        records = self._run_records_index.get(run_id, [])
        ordered = sorted(records, key=lambda record: (record.timestamp, record.sequence))
        return [self._to_stored_event(record) for record in ordered]

    def list_all(self) -> list[StoredEvent]:
        records = [
            record
            for run_records in self._run_records_index.values()
            for record in run_records
        ]
        ordered = sorted(records, key=lambda record: (record.timestamp, record.sequence))
        return [self._to_stored_event(record) for record in ordered]

    def _to_stored_event(self, record: _StoredRecord) -> StoredEvent:
        return StoredEvent(
            id=record.id,
            timestamp=record.timestamp,
            run_id=record.run_id,
            payload=deepcopy(record.payload),
            integrity_warning=record.integrity_warning,
        )


