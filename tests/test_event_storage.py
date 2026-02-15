from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.errors import StorageReadError, StorageWriteError  # noqa: E402
from nightledger_api.services.event_ingest_service import validate_event_payload  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402

client = TestClient(app)


def valid_event_payload() -> dict[str, object]:
    return {
        "id": "evt_123",
        "run_id": "run_123",
        "timestamp": "2026-02-14T13:00:00Z",
        "type": "action",
        "actor": "agent",
        "title": "Attempt transfer",
        "details": "Agent is about to transfer funds",
        "confidence": 0.8,
        "risk_level": "high",
        "requires_approval": True,
        "approval": {
            "status": "pending",
            "requested_by": "agent",
            "resolved_by": None,
            "resolved_at": None,
            "reason": None,
        },
        "evidence": [
            {"kind": "log", "label": "Execution log", "ref": "log://transfer-1"}
        ],
        "meta": {"workflow": "triage_inbox", "step": "classify_priority"},
    }


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_store_retrieval_does_not_allow_mutating_history() -> None:
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    event = validate_event_payload(payload)

    store.append(event)
    first_read = store.list_by_run_id("run_123")
    first_read[0].payload["title"] = "Tampered title"
    second_read = store.list_by_run_id("run_123")

    assert second_read[0].payload["title"] == "Attempt transfer"


def test_get_run_events_returns_deterministic_ascending_order() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    newer = valid_event_payload()
    newer["id"] = "evt_newer"
    newer["run_id"] = "run_456"
    newer["timestamp"] = "2026-02-14T13:00:00Z"

    older = valid_event_payload()
    older["id"] = "evt_older"
    older["run_id"] = "run_456"
    older["timestamp"] = "2026-02-14T12:00:00Z"

    assert client.post("/v1/events", json=newer).status_code == 201
    assert client.post("/v1/events", json=older).status_code == 201

    response = client.get("/v1/runs/run_456/events")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_456"
    events = body["events"]
    assert [event["id"] for event in events] == ["evt_older", "evt_newer"]
    assert set(events[0].keys()) == {"id", "timestamp", "run_id", "payload", "integrity_warning"}


class _FailingAppendStore:
    def append(self, event: object) -> object:
        _ = event
        raise StorageWriteError("storage backend append failed")

    def list_by_run_id(self, run_id: str) -> list[object]:
        _ = run_id
        return []


class _FailingReadStore:
    def append(self, event: object) -> object:
        _ = event
        return object()

    def list_by_run_id(self, run_id: str) -> list[object]:
        _ = run_id
        raise StorageReadError("storage backend read failed")


def test_post_events_returns_structured_storage_write_error() -> None:
    app.dependency_overrides[get_event_store] = lambda: _FailingAppendStore()

    response = client.post("/v1/events", json=valid_event_payload())

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_WRITE_ERROR"
    assert body["error"]["message"] == "Failed to persist event"
    assert body["error"]["details"] == [
        {
            "path": "storage",
            "message": "storage backend append failed",
            "type": "storage_failure",
            "code": "STORAGE_APPEND_FAILED",
        }
    ]


def test_get_run_events_returns_structured_storage_read_error() -> None:
    app.dependency_overrides[get_event_store] = lambda: _FailingReadStore()

    response = client.get("/v1/runs/run_123/events")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_READ_ERROR"
    assert body["error"]["message"] == "Failed to load events"
    assert body["error"]["details"] == [
        {
            "path": "storage",
            "message": "storage backend read failed",
            "type": "storage_failure",
            "code": "STORAGE_READ_FAILED",
        }
    ]


# ============================================================================
# Additional Tests for Issue #21 — Comprehensive Storage Coverage
# ============================================================================


def test_all_appended_events_are_retrievable() -> None:
    """Test append-only semantics: no data loss."""
    store = InMemoryAppendOnlyEventStore()
    
    # Append 5 events
    for i in range(5):
        payload = valid_event_payload()
        payload["id"] = f"evt_{i}"
        payload["run_id"] = "run_test"
        event = validate_event_payload(payload)
        store.append(event)
    
    # Verify all 5 are retrievable
    events = store.list_by_run_id("run_test")
    assert len(events) == 5
    assert [e.id for e in events] == [f"evt_{i}" for i in range(5)]


def test_store_has_no_delete_or_update_methods() -> None:
    """Test append-only API contract: no mutation methods exist."""
    store = InMemoryAppendOnlyEventStore()
    
    assert not hasattr(store, "delete")
    assert not hasattr(store, "update")
    assert not hasattr(store, "remove")
    assert not hasattr(store, "clear")


def test_sequence_is_monotonically_increasing() -> None:
    """Test internal sequence increases monotonically regardless of timestamp."""
    store = InMemoryAppendOnlyEventStore()
    
    # Append 3 events with timestamps in reverse order
    for i, hour in [(0, 15), (1, 14), (2, 13)]:
        payload = valid_event_payload()
        payload["id"] = f"evt_{i}"
        payload["run_id"] = "run_seq"
        payload["timestamp"] = f"2026-02-14T{hour}:00:00Z"
        event = validate_event_payload(payload)
        store.append(event)
    
    # Verify retrieval is ordered by timestamp (ascending), not insertion order
    events = store.list_by_run_id("run_seq")
    assert [e.id for e in events] == ["evt_2", "evt_1", "evt_0"]


def test_events_for_different_run_ids_are_isolated() -> None:
    """Test run isolation: events for different run_ids don't cross-contaminate."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    payload_a = valid_event_payload()
    payload_a["id"] = "evt_a"
    payload_a["run_id"] = "run_a"
    
    payload_b = valid_event_payload()
    payload_b["id"] = "evt_b"
    payload_b["run_id"] = "run_b"
    
    client.post("/v1/events", json=payload_a)
    client.post("/v1/events", json=payload_b)
    
    response_a = client.get("/v1/runs/run_a/events")
    response_b = client.get("/v1/runs/run_b/events")
    
    assert response_a.json()["events"][0]["id"] == "evt_a"
    assert response_b.json()["events"][0]["id"] == "evt_b"
    assert len(response_a.json()["events"]) == 1
    assert len(response_b.json()["events"]) == 1


def test_empty_run_returns_empty_list() -> None:
    """Test querying a run_id with no events returns 200 with empty array."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    response = client.get("/v1/runs/nonexistent_run/events")
    
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "nonexistent_run"
    assert body["events"] == []


def test_same_timestamp_tiebreaking_by_sequence() -> None:
    """Test deterministic ordering when timestamps are identical."""
    store = InMemoryAppendOnlyEventStore()
    
    # Append 3 events with identical timestamps
    for i in range(3):
        payload = valid_event_payload()
        payload["id"] = f"evt_{i}"
        payload["run_id"] = "run_tie"
        payload["timestamp"] = "2026-02-14T13:00:00Z"
        event = validate_event_payload(payload)
        store.append(event)
    
    events = store.list_by_run_id("run_tie")
    
    # Should be ordered by insertion sequence
    assert [e.id for e in events] == ["evt_0", "evt_1", "evt_2"]


def test_many_events_ordering_with_randomized_timestamps() -> None:
    """Test ordering with many events inserted in random timestamp order."""
    import random
    
    store = InMemoryAppendOnlyEventStore()
    
    hours = list(range(10, 20))  # 10 different hours
    random.shuffle(hours)
    
    for i, hour in enumerate(hours):
        payload = valid_event_payload()
        payload["id"] = f"evt_{hour}"
        payload["run_id"] = "run_many"
        payload["timestamp"] = f"2026-02-14T{hour}:00:00Z"
        event = validate_event_payload(payload)
        store.append(event)
    
    events = store.list_by_run_id("run_many")
    
    # Should be strictly ascending by timestamp
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)
    assert [e.id for e in events] == [f"evt_{h}" for h in range(10, 20)]


def test_stored_envelope_contains_correct_fields() -> None:
    """Test StoredEvent envelope has id, timestamp, run_id, payload."""
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    event = validate_event_payload(payload)
    
    stored = store.append(event)
    
    assert hasattr(stored, "id")
    assert hasattr(stored, "timestamp")
    assert hasattr(stored, "run_id")
    assert hasattr(stored, "payload")
    assert isinstance(stored.payload, dict)
    assert stored.id == "evt_123"
    assert stored.run_id == "run_123"


def test_stored_event_timestamp_is_utc_normalized() -> None:
    """Test stored timestamp is UTC even when input has offset."""
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    payload["timestamp"] = "2026-02-14T15:00:00+02:00"  # +02:00 offset
    event = validate_event_payload(payload)
    
    stored = store.append(event)
    
    assert stored.timestamp.hour == 13  # Normalized to UTC
    assert stored.timestamp.tzinfo is not None
    assert stored.timestamp.tzinfo.tzname(None) == "UTC"


def test_append_return_value_matches_stored_data() -> None:
    """Test append() return value matches what list_by_run_id returns."""
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    event = validate_event_payload(payload)
    
    returned = store.append(event)
    retrieved = store.list_by_run_id("run_123")[0]
    
    assert returned.id == retrieved.id
    assert returned.timestamp == retrieved.timestamp
    assert returned.run_id == retrieved.run_id
    assert returned.payload == retrieved.payload


def test_post_get_round_trip() -> None:
    """Test full API round-trip: POST event, GET run, verify event appears."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    payload = valid_event_payload()
    payload["id"] = "evt_roundtrip"
    payload["run_id"] = "run_roundtrip"
    
    post_response = client.post("/v1/events", json=payload)
    assert post_response.status_code == 201
    
    get_response = client.get("/v1/runs/run_roundtrip/events")
    assert get_response.status_code == 200
    
    body = get_response.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["id"] == "evt_roundtrip"
    assert body["events"][0]["payload"]["title"] == "Attempt transfer"


def test_get_missing_run_returns_200_with_empty_array() -> None:
    """Test GET for missing run_id returns 200 (not 404) with empty events array."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    response = client.get("/v1/runs/missing_run/events")
    
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "missing_run"
    assert body["events"] == []
    assert isinstance(body["events"], list)


def test_duplicate_event_id_within_run_is_rejected() -> None:
    """Test RULE-CORE-003: duplicate event_id within run_id is rejected."""
    from nightledger_api.services.errors import DuplicateEventError
    
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    payload = valid_event_payload()
    payload["id"] = "evt_duplicate"
    payload["run_id"] = "run_dup"
    
    # First POST should succeed
    response1 = client.post("/v1/events", json=payload)
    assert response1.status_code == 201
    
    # Second POST with same id + run_id should fail
    response2 = client.post("/v1/events", json=payload)
    assert response2.status_code == 409  # Conflict
    body = response2.json()
    assert body["error"]["code"] == "DUPLICATE_EVENT_ID"
    assert body["error"]["message"] == "Event ID already exists for this run"


def test_get_response_timestamps_use_z_suffix() -> None:
    """Test GET response serializes timestamps with Z suffix, not +00:00."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    payload = valid_event_payload()
    payload["id"] = "evt_tz"
    payload["run_id"] = "run_tz"
    payload["timestamp"] = "2026-02-14T13:00:00Z"
    
    client.post("/v1/events", json=payload)
    response = client.get("/v1/runs/run_tz/events")
    
    timestamp_str = response.json()["events"][0]["timestamp"]
    assert timestamp_str.endswith("Z"), f"Expected Z suffix, got: {timestamp_str}"
    assert "+00:00" not in timestamp_str


# ============================================================================
# Round 2 — Storage Optimizations (TDD)
# ============================================================================


def test_same_event_id_in_different_runs_is_accepted() -> None:
    """Test that duplicate event_id across different run_ids is allowed."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    payload_a = valid_event_payload()
    payload_a["id"] = "evt_shared_id"
    payload_a["run_id"] = "run_alpha"

    payload_b = valid_event_payload()
    payload_b["id"] = "evt_shared_id"  # Same event_id
    payload_b["run_id"] = "run_beta"   # Different run_id

    response_a = client.post("/v1/events", json=payload_a)
    response_b = client.post("/v1/events", json=payload_b)

    assert response_a.status_code == 201
    assert response_b.status_code == 201

    # Both runs have exactly one event
    assert len(store.list_by_run_id("run_alpha")) == 1
    assert len(store.list_by_run_id("run_beta")) == 1


def test_out_of_order_timestamp_marks_integrity_warning() -> None:
    """Test RULE-CORE-005: out-of-order timestamp sets integrity_warning=True."""
    store = InMemoryAppendOnlyEventStore()

    # First event at 15:00
    newer = valid_event_payload()
    newer["id"] = "evt_first"
    newer["run_id"] = "run_order"
    newer["timestamp"] = "2026-02-14T15:00:00Z"
    event_newer = validate_event_payload(newer)
    stored_first = store.append(event_newer)

    # Second event at 13:00 (out of order)
    older = valid_event_payload()
    older["id"] = "evt_second"
    older["run_id"] = "run_order"
    older["timestamp"] = "2026-02-14T13:00:00Z"
    event_older = validate_event_payload(older)
    stored_second = store.append(event_older)

    # First event should NOT have integrity_warning
    assert stored_first.integrity_warning is False

    # Second event (out of order) SHOULD have integrity_warning
    assert stored_second.integrity_warning is True

    # Warning should persist in retrieval
    events = store.list_by_run_id("run_order")
    warnings = {e.id: e.integrity_warning for e in events}
    assert warnings["evt_first"] is False
    assert warnings["evt_second"] is True


def test_post_response_includes_event_id() -> None:
    """Test POST /v1/events response includes the persisted event_id."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    payload = valid_event_payload()
    payload["id"] = "evt_response_check"
    payload["run_id"] = "run_response"

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_id"] == "evt_response_check"


def test_duplicate_index_uses_efficient_lookup() -> None:
    """Test the store uses an efficient index (not O(n) scan per append)."""
    store = InMemoryAppendOnlyEventStore()

    # The store should have an internal index structure
    assert hasattr(store, "_event_id_index"), (
        "Store should have _event_id_index for O(1) duplicate lookups"
    )
    assert isinstance(store._event_id_index, dict)

    # After appending, the index should be populated
    payload = valid_event_payload()
    payload["id"] = "evt_indexed"
    payload["run_id"] = "run_index"
    event = validate_event_payload(payload)
    store.append(event)

    assert "run_index" in store._event_id_index
    assert "evt_indexed" in store._event_id_index["run_index"]


def test_event_store_protocol_documents_exceptions() -> None:
    """Test that EventStore Protocol append method has proper type hints."""
    from nightledger_api.services.event_store import EventStore
    import inspect

    # The Protocol's append method should document raising DuplicateEventError
    append_doc = inspect.getdoc(EventStore.append)
    assert append_doc is not None, "EventStore.append should have a docstring"
    assert "DuplicateEventError" in append_doc, (
        "EventStore.append docstring should mention DuplicateEventError"
    )


# ============================================================================
# Round 3 — Performance & API Completeness (TDD)
# ============================================================================


def test_get_response_includes_integrity_warning() -> None:
    """Test GET response exposes integrity_warning field per RULE-CORE-005."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    # First event (in order)
    payload1 = valid_event_payload()
    payload1["id"] = "evt_first"
    payload1["run_id"] = "run_warn"
    payload1["timestamp"] = "2026-02-14T15:00:00Z"
    client.post("/v1/events", json=payload1)

    # Second event (out of order)
    payload2 = valid_event_payload()
    payload2["id"] = "evt_second"
    payload2["run_id"] = "run_warn"
    payload2["timestamp"] = "2026-02-14T13:00:00Z"
    client.post("/v1/events", json=payload2)

    response = client.get("/v1/runs/run_warn/events")
    events = response.json()["events"]

    # Events are returned in timestamp order (ascending)
    # events[0] = evt_second at 13:00 (out of order, warning=True)
    # events[1] = evt_first at 15:00 (in order, warning=False)
    assert "integrity_warning" in events[0]
    assert "integrity_warning" in events[1]
    assert events[0]["integrity_warning"] is True   # evt_second (out of order)
    assert events[1]["integrity_warning"] is False  # evt_first (in order)


def test_post_response_includes_integrity_warning() -> None:
    """Test POST response includes integrity_warning to inform caller."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    # First event
    payload1 = valid_event_payload()
    payload1["id"] = "evt_post_first"
    payload1["run_id"] = "run_post_warn"
    payload1["timestamp"] = "2026-02-14T15:00:00Z"
    response1 = client.post("/v1/events", json=payload1)

    body1 = response1.json()
    assert "integrity_warning" in body1
    assert body1["integrity_warning"] is False

    # Second event (out of order)
    payload2 = valid_event_payload()
    payload2["id"] = "evt_post_second"
    payload2["run_id"] = "run_post_warn"
    payload2["timestamp"] = "2026-02-14T13:00:00Z"
    response2 = client.post("/v1/events", json=payload2)

    body2 = response2.json()
    assert "integrity_warning" in body2
    assert body2["integrity_warning"] is True


def test_list_by_run_id_uses_efficient_index() -> None:
    """Test store uses O(1) run_id index, not O(n) scan."""
    store = InMemoryAppendOnlyEventStore()

    # Store should have a run_records index
    assert hasattr(store, "_run_records_index"), (
        "Store should have _run_records_index for O(1) run lookups"
    )
    assert isinstance(store._run_records_index, dict)

    # After appending, the index should be populated
    payload = valid_event_payload()
    payload["id"] = "evt_run_idx"
    payload["run_id"] = "run_idx_test"
    event = validate_event_payload(payload)
    store.append(event)

    assert "run_idx_test" in store._run_records_index
    assert len(store._run_records_index["run_idx_test"]) == 1


def test_out_of_order_detection_uses_efficient_timestamp_tracking() -> None:
    """Test store tracks last timestamp per run for O(1) out-of-order detection."""
    store = InMemoryAppendOnlyEventStore()

    # Store should have timestamp tracking
    assert hasattr(store, "_last_timestamp_by_run"), (
        "Store should have _last_timestamp_by_run for O(1) out-of-order checks"
    )
    assert isinstance(store._last_timestamp_by_run, dict)

    # After appending, the timestamp should be tracked
    payload = valid_event_payload()
    payload["id"] = "evt_ts_track"
    payload["run_id"] = "run_ts_test"
    payload["timestamp"] = "2026-02-14T15:00:00Z"
    event = validate_event_payload(payload)
    store.append(event)

    assert "run_ts_test" in store._last_timestamp_by_run
    assert store._last_timestamp_by_run["run_ts_test"] == event.timestamp


def test_get_response_includes_event_count() -> None:
    """Test GET response includes event_count metadata."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    # Append 3 events
    for i in range(3):
        payload = valid_event_payload()
        payload["id"] = f"evt_count_{i}"
        payload["run_id"] = "run_count"
        client.post("/v1/events", json=payload)

    response = client.get("/v1/runs/run_count/events")
    body = response.json()

    assert "event_count" in body
    assert body["event_count"] == 3
    assert len(body["events"]) == 3


# ============================================================================
# Round 4 — Data Integrity & API Completeness (TDD)
# ============================================================================


def test_append_return_value_payload_is_immutable() -> None:
    """Test that mutating the payload dict from append() return value doesn't corrupt storage."""
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    event = validate_event_payload(payload)
    
    stored = store.append(event)
    
    # Attempt to mutate the returned payload
    stored.payload["title"] = "HACKED"
    
    # Retrieve the event and verify it wasn't mutated
    retrieved = store.list_by_run_id("run_123")[0]
    assert retrieved.payload["title"] == "Attempt transfer"


def test_empty_run_id_is_rejected() -> None:
    """Test that empty run_id is rejected per RULE-CORE-001 intent."""
    payload = valid_event_payload()
    payload["run_id"] = ""  # Empty string
    
    response = client.post("/v1/events", json=payload)
    
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "SCHEMA_VALIDATION_ERROR"
    # Should have a validation error for run_id
    details = {d["path"]: d for d in body["error"]["details"]}
    assert "run_id" in details


def test_store_does_not_maintain_redundant_records_list() -> None:
    """Test that store doesn't maintain the redundant _records list."""
    store = InMemoryAppendOnlyEventStore()
    
    # Store should NOT have _records attribute
    assert not hasattr(store, "_records"), (
        "Store should not maintain redundant _records list after round 3 optimizations"
    )


def test_get_empty_run_includes_event_count_zero() -> None:
    """Test GET for empty run returns event_count: 0."""
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    
    response = client.get("/v1/runs/empty_run/events")
    
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "empty_run"
    assert body["event_count"] == 0
    assert body["events"] == []


def test_list_by_run_id_protocol_has_docstring() -> None:
    """Test that EventStore Protocol list_by_run_id has a docstring."""
    from nightledger_api.services.event_store import EventStore
    import inspect
    
    docstring = inspect.getdoc(EventStore.list_by_run_id)
    assert docstring is not None, "EventStore.list_by_run_id should have a docstring"
    assert "run_id" in docstring.lower(), "Docstring should mention run_id"


def test_duplicate_event_error_has_structured_fields() -> None:
    """Test DuplicateEventError carries event_id and run_id as structured fields."""
    from nightledger_api.services.errors import DuplicateEventError
    
    store = InMemoryAppendOnlyEventStore()
    payload = valid_event_payload()
    payload["id"] = "evt_struct"
    payload["run_id"] = "run_struct"
    event = validate_event_payload(payload)
    
    # First append succeeds
    store.append(event)
    
    # Second append should raise DuplicateEventError with structured fields
    try:
        store.append(event)
        assert False, "Should have raised DuplicateEventError"
    except DuplicateEventError as exc:
        assert hasattr(exc, "event_id"), "DuplicateEventError should have event_id field"
        assert hasattr(exc, "run_id"), "DuplicateEventError should have run_id field"
        assert exc.event_id == "evt_struct"
        assert exc.run_id == "run_struct"


# ============================================================================
# Round 5 — Code Hygiene & Documentation (TDD)
# ============================================================================


def test_duplicate_event_presenter_uses_structured_fields() -> None:
    """Test presenter uses exc.event_id and exc.run_id, not str(exc)."""
    from nightledger_api.services.errors import DuplicateEventError
    from nightledger_api.presenters.error_presenter import present_duplicate_event_error
    
    exc = DuplicateEventError(event_id="evt_test", run_id="run_test")
    result = present_duplicate_event_error(exc)
    
    # The message should include the structured fields
    message = result["error"]["details"][0]["message"]
    assert "evt_test" in message
    assert "run_test" in message
    
    # Verify it's not just using str(exc) by checking the exact format
    # If using structured fields, we can control the exact message format
    assert message == "Event ID 'evt_test' already exists for run 'run_test'"


def test_empty_run_id_returns_missing_run_id_error_code() -> None:
    """Test empty run_id produces MISSING_RUN_ID error code, not generic SCHEMA_VALIDATION_ERROR."""
    payload = valid_event_payload()
    payload["run_id"] = ""  # Empty string
    
    response = client.post("/v1/events", json=payload)
    
    assert response.status_code == 422
    body = response.json()
    details = {d["path"]: d for d in body["error"]["details"]}
    
    # Should map to MISSING_RUN_ID (same as RULE-CORE-001)
    assert "run_id" in details
    assert details["run_id"]["code"] == "MISSING_RUN_ID"


def test_api_docs_specify_run_id_min_length() -> None:
    """Test API.md documents that run_id must be non-empty."""
    import re
    
    api_md_path = Path(__file__).resolve().parents[1] / "spec" / "API.md"
    api_md_content = api_md_path.read_text()
    
    # Should mention run_id constraint somewhere in field constraints section
    # Look for pattern like "run_id must be non-empty" or "min_length" or similar
    constraints_section = re.search(
        r"Field constraints:.*?(?=##|\Z)", 
        api_md_content, 
        re.DOTALL | re.IGNORECASE
    )
    
    assert constraints_section is not None, "API.md should have Field constraints section"
    constraints_text = constraints_section.group(0)
    
    # Should mention run_id and non-empty or min_length
    assert "run_id" in constraints_text.lower(), (
        "Field constraints should mention run_id"
    )
    assert any(keyword in constraints_text.lower() for keyword in ["non-empty", "min_length", "must not be empty"]), (
        "Field constraints should specify run_id must be non-empty"
    )




