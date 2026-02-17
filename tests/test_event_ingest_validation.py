from pathlib import Path
import sys
from datetime import timedelta, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_ingest_service import validate_event_payload  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store
    yield
    app.dependency_overrides.clear()


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


def extract_error_paths(body: dict[str, object]) -> set[str]:
    error = body["error"]
    details = error["details"]
    return {detail["path"] for detail in details}


def extract_error_details(body: dict[str, object]) -> dict[str, dict[str, str]]:
    error = body["error"]
    details = error["details"]
    return {detail["path"]: detail for detail in details}


def test_post_events_accepts_valid_payload() -> None:
    payload = valid_event_payload()
    payload["id"] = "evt_valid_payload"
    response = client.post("/v1/events", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_id"] == "evt_valid_payload"


def test_post_events_rejects_missing_required_fields_with_structured_errors() -> None:
    invalid_payload = {
        "run_id": "run_123",
        "timestamp": "2026-02-14T13:00:00Z",
        "actor": "agent",
        "details": "Trying to execute a risky action",
    }

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "SCHEMA_VALIDATION_ERROR"
    assert body["error"]["message"]
    assert isinstance(body["error"]["details"], list)
    paths = extract_error_paths(body)
    assert "id" in paths
    assert "type" in paths
    assert "title" in paths
    assert "approval" in paths
    details = extract_error_details(body)
    assert details["id"]["code"] == "MISSING_EVENT_ID"
    assert details["type"]["code"] == "MISSING_EVENT_TYPE"
    assert details["title"]["code"] == "MISSING_TIMELINE_FIELDS"
    assert details["approval"]["code"] == "MISSING_APPROVAL"


def test_post_events_returns_validation_details_sorted_by_path() -> None:
    invalid_payload = {
        "run_id": "run_123",
        "timestamp": "2026-02-14T13:00:00Z",
        "actor": "agent",
        "details": "Trying to execute a risky action",
    }

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = response.json()["error"]["details"]
    paths = [detail["path"] for detail in details]
    assert paths == sorted(paths)


def test_post_events_rejects_invalid_enum_values() -> None:
    invalid_payload = valid_event_payload()
    invalid_payload["type"] = "unknown"
    invalid_payload["actor"] = "bot"
    invalid_payload["approval"]["status"] = "waiting"
    invalid_payload["evidence"][0]["kind"] = "file"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    paths = extract_error_paths(response.json())
    assert "type" in paths
    assert "actor" in paths
    assert "approval.status" in paths
    assert "evidence.0.kind" in paths
    details = extract_error_details(response.json())
    assert details["type"]["code"] == "INVALID_EVENT_TYPE"
    assert details["actor"]["code"] == "INVALID_ACTOR"
    assert details["approval.status"]["code"] == "INVALID_APPROVAL_STATUS"
    assert details["evidence.0.kind"]["code"] == "INVALID_EVIDENCE_KIND"


def test_post_events_rejects_unknown_fields() -> None:
    invalid_payload = valid_event_payload()
    invalid_payload["surprise"] = "nope"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    paths = extract_error_paths(response.json())
    assert "surprise" in paths
    details = extract_error_details(response.json())
    assert details["surprise"]["code"] == "UNKNOWN_FIELD"


def test_post_events_rejects_out_of_bounds_confidence() -> None:
    invalid_payload = valid_event_payload()
    invalid_payload["confidence"] = 1.5

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    paths = extract_error_paths(response.json())
    assert "confidence" in paths
    details = extract_error_details(response.json())
    assert details["confidence"]["code"] == "INVALID_CONFIDENCE_BOUNDS"


def test_post_events_rejects_blank_title_and_details() -> None:
    invalid_payload = valid_event_payload()
    invalid_payload["title"] = "   "
    invalid_payload["details"] = ""

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    paths = extract_error_paths(response.json())
    assert "title" in paths
    assert "details" in paths
    details = extract_error_details(response.json())
    assert details["title"]["code"] == "MISSING_TIMELINE_FIELDS"
    assert details["details"]["code"] == "MISSING_TIMELINE_FIELDS"


def test_post_events_rejects_timestamp_without_timezone() -> None:
    invalid_payload = valid_event_payload()
    invalid_payload["timestamp"] = "2026-02-14T13:00:00"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert details["timestamp"]["code"] == "INVALID_TIMESTAMP"


def test_validate_event_payload_normalizes_offset_timestamp_to_utc() -> None:
    payload = valid_event_payload()
    payload["timestamp"] = "2026-02-14T15:00:00+02:00"

    event = validate_event_payload(payload)

    assert event.timestamp.utcoffset() == timedelta(0)
    assert event.timestamp.tzinfo == timezone.utc
    assert event.timestamp.hour == 13


def test_post_events_rejects_missing_run_id() -> None:
    """Test missing run_id produces MISSING_RUN_ID error code."""
    invalid_payload = valid_event_payload()
    del invalid_payload["run_id"]

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "run_id" in details
    assert details["run_id"]["code"] == "MISSING_RUN_ID"


def test_post_events_rejects_missing_timestamp() -> None:
    """Test missing timestamp produces MISSING_TIMESTAMP error code."""
    invalid_payload = valid_event_payload()
    del invalid_payload["timestamp"]

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "timestamp" in details
    assert details["timestamp"]["code"] == "MISSING_TIMESTAMP"


def test_post_events_rejects_missing_actor() -> None:
    """Test missing actor produces MISSING_ACTOR error code."""
    invalid_payload = valid_event_payload()
    del invalid_payload["actor"]

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "actor" in details
    assert details["actor"]["code"] == "MISSING_ACTOR"


def test_post_events_rejects_negative_confidence() -> None:
    """Test confidence < 0 produces INVALID_CONFIDENCE_BOUNDS error."""
    invalid_payload = valid_event_payload()
    invalid_payload["confidence"] = -0.1

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "confidence" in details
    assert details["confidence"]["code"] == "INVALID_CONFIDENCE_BOUNDS"


def test_post_events_accepts_confidence_boundary_values() -> None:
    """Test confidence = 0.0 and 1.0 are accepted."""
    # Test lower boundary
    payload_lower = valid_event_payload()
    payload_lower["id"] = "evt_conf_lower"
    payload_lower["confidence"] = 0.0
    response_lower = client.post("/v1/events", json=payload_lower)
    assert response_lower.status_code == 201

    # Test upper boundary
    payload_upper = valid_event_payload()
    payload_upper["id"] = "evt_conf_upper"
    payload_upper["confidence"] = 1.0
    response_upper = client.post("/v1/events", json=payload_upper)
    assert response_upper.status_code == 201


def test_post_events_rejects_non_numeric_confidence() -> None:
    """Test confidence as string produces INVALID_CONFIDENCE_TYPE error."""
    invalid_payload = valid_event_payload()
    invalid_payload["confidence"] = "high"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "confidence" in details
    assert details["confidence"]["code"] == "INVALID_CONFIDENCE_TYPE"


def test_post_events_rejects_invalid_risk_level() -> None:
    """Test invalid risk_level enum produces INVALID_RISK_LEVEL error."""
    invalid_payload = valid_event_payload()
    invalid_payload["risk_level"] = "critical"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "risk_level" in details
    assert details["risk_level"]["code"] == "INVALID_RISK_LEVEL"


def test_post_events_rejects_unknown_field_in_approval() -> None:
    """Test unknown field inside approval object produces UNKNOWN_FIELD error."""
    invalid_payload = valid_event_payload()
    invalid_payload["approval"]["extra_field"] = "nope"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "approval.extra_field" in details
    assert details["approval.extra_field"]["code"] == "UNKNOWN_FIELD"


def test_post_events_rejects_unknown_field_in_evidence() -> None:
    """Test unknown field inside evidence item produces UNKNOWN_FIELD error."""
    invalid_payload = valid_event_payload()
    invalid_payload["evidence"][0]["extra_field"] = "nope"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "evidence.0.extra_field" in details
    assert details["evidence.0.extra_field"]["code"] == "UNKNOWN_FIELD"


def test_post_events_rejects_incomplete_evidence_item() -> None:
    """Test evidence item missing required fields produces validation errors."""
    invalid_payload = valid_event_payload()
    invalid_payload["evidence"] = [{}]

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "evidence.0.kind" in details
    assert "evidence.0.label" in details
    assert "evidence.0.ref" in details


def test_post_events_accepts_empty_evidence_array() -> None:
    """Test empty evidence array is accepted (default value)."""
    payload = valid_event_payload()
    payload["id"] = "evt_empty_evidence"
    payload["evidence"] = []

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 201


def test_post_events_rejects_unknown_field_in_meta() -> None:
    """Test unknown field inside meta object produces UNKNOWN_FIELD error."""
    invalid_payload = valid_event_payload()
    invalid_payload["meta"]["surprise"] = "nope"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "meta.surprise" in details
    assert details["meta.surprise"]["code"] == "UNKNOWN_FIELD"


def test_post_events_rejects_completely_empty_payload() -> None:
    """Test empty payload produces errors for all required fields."""
    response = client.post("/v1/events", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "SCHEMA_VALIDATION_ERROR"
    details = extract_error_details(body)
    
    # All 8 required fields should appear in errors
    required_fields = {"id", "run_id", "timestamp", "type", "actor", "title", "details", "approval"}
    error_paths = set(details.keys())
    assert required_fields.issubset(error_paths)


def test_post_events_rejects_invalid_timestamp_format() -> None:
    """Test completely invalid timestamp format produces INVALID_TIMESTAMP error."""
    invalid_payload = valid_event_payload()
    invalid_payload["timestamp"] = "not-a-date"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    details = extract_error_details(response.json())
    assert "timestamp" in details
    assert details["timestamp"]["code"] == "INVALID_TIMESTAMP"


def test_post_events_accumulates_errors_across_depth_levels() -> None:
    """Test errors from multiple nesting levels are collected and sorted."""
    invalid_payload = valid_event_payload()
    invalid_payload["type"] = "unknown"
    invalid_payload["approval"]["status"] = "waiting"
    invalid_payload["evidence"][0]["kind"] = "file"

    response = client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422
    body = response.json()
    details_list = body["error"]["details"]
    
    # Should have at least 3 errors
    assert len(details_list) >= 3
    
    # Verify they're sorted by path
    paths = [detail["path"] for detail in details_list]
    assert paths == sorted(paths)
    
    # Verify all three errors are present
    details = extract_error_details(body)
    assert "type" in details
    assert "approval.status" in details
    assert "evidence.0.kind" in details


def test_post_events_accepts_payload_without_confidence() -> None:
    """Test confidence field is optional and can be omitted."""
    payload = valid_event_payload()
    payload["id"] = "evt_no_confidence"
    del payload["confidence"]

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 201


def test_get_events_returns_method_not_allowed() -> None:
    """Test GET /v1/events returns 405 Method Not Allowed."""
    response = client.get("/v1/events")

    assert response.status_code == 405


def test_post_events_rejects_approval_requested_without_pending_status() -> None:
    payload = valid_event_payload()
    payload["id"] = "evt_invalid_approval_requested_status"
    payload["type"] = "approval_requested"
    payload["requires_approval"] = True
    payload["approval"]["status"] = "not_required"

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "approval.status",
            "message": "approval_requested must use approval.status='pending'",
            "type": "state_conflict",
            "code": "INVALID_APPROVAL_TRANSITION",
            "rule_id": "RULE-GATE-001",
        }
    ]


def test_post_events_rejects_approval_requested_without_requires_approval() -> None:
    payload = valid_event_payload()
    payload["id"] = "evt_invalid_approval_requested_requires_flag"
    payload["type"] = "approval_requested"
    payload["requires_approval"] = False
    payload["approval"]["status"] = "pending"

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "requires_approval",
            "message": "approval_requested must set requires_approval=true",
            "type": "state_conflict",
            "code": "INVALID_APPROVAL_TRANSITION",
            "rule_id": "RULE-GATE-001",
        }
    ]


def test_post_events_rejects_approval_resolved_without_pending_gate() -> None:
    payload = valid_event_payload()
    payload["id"] = "evt_invalid_approval_resolved_without_pending"
    payload["type"] = "approval_resolved"
    payload["requires_approval"] = True
    payload["approval"]["status"] = "approved"
    payload["approval"]["resolved_by"] = "human_reviewer"
    payload["approval"]["resolved_at"] = "2026-02-14T13:00:00Z"

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "approval",
            "message": "approval_resolved encountered without pending approval",
            "type": "state_conflict",
            "code": "NO_PENDING_APPROVAL",
            "rule_id": "RULE-GATE-002",
        }
    ]


def test_post_events_rejects_resolved_approval_without_approver_id() -> None:
    pending_payload = valid_event_payload()
    pending_payload["id"] = "evt_pending_for_missing_approver"
    pending_payload["type"] = "approval_requested"
    pending_payload["requires_approval"] = True
    pending_payload["approval"]["status"] = "pending"
    pending_payload["approval"]["requested_by"] = "agent"
    pending_payload["approval"]["resolved_by"] = None
    pending_payload["approval"]["resolved_at"] = None
    assert client.post("/v1/events", json=pending_payload).status_code == 201

    invalid_resolution_payload = valid_event_payload()
    invalid_resolution_payload["id"] = "evt_missing_approver_resolution"
    invalid_resolution_payload["type"] = "approval_resolved"
    invalid_resolution_payload["requires_approval"] = True
    invalid_resolution_payload["approval"]["status"] = "approved"
    invalid_resolution_payload["approval"]["requested_by"] = "agent"
    invalid_resolution_payload["approval"]["resolved_by"] = None
    invalid_resolution_payload["approval"]["resolved_at"] = "2026-02-14T13:00:10Z"

    response = client.post("/v1/events", json=invalid_resolution_payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "approval.resolved_by",
            "message": "approval_resolved is missing approver identity",
            "type": "state_conflict",
            "code": "MISSING_APPROVER_ID",
            "rule_id": "RULE-GATE-007",
        }
    ]


def test_post_events_rejects_resolved_approval_without_resolution_timestamp() -> None:
    pending_payload = valid_event_payload()
    pending_payload["id"] = "evt_pending_for_missing_resolution_ts"
    pending_payload["type"] = "approval_requested"
    pending_payload["requires_approval"] = True
    pending_payload["approval"]["status"] = "pending"
    pending_payload["approval"]["requested_by"] = "agent"
    pending_payload["approval"]["resolved_by"] = None
    pending_payload["approval"]["resolved_at"] = None
    assert client.post("/v1/events", json=pending_payload).status_code == 201

    invalid_resolution_payload = valid_event_payload()
    invalid_resolution_payload["id"] = "evt_missing_resolution_ts"
    invalid_resolution_payload["type"] = "approval_resolved"
    invalid_resolution_payload["requires_approval"] = True
    invalid_resolution_payload["approval"]["status"] = "approved"
    invalid_resolution_payload["approval"]["requested_by"] = "agent"
    invalid_resolution_payload["approval"]["resolved_by"] = "human_reviewer"
    invalid_resolution_payload["approval"]["resolved_at"] = None

    response = client.post("/v1/events", json=invalid_resolution_payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "approval.resolved_at",
            "message": "approval_resolved is missing resolution timestamp",
            "type": "state_conflict",
            "code": "MISSING_APPROVAL_TIMESTAMP",
            "rule_id": "RULE-GATE-008",
        }
    ]


def test_post_events_rejects_mutating_event_after_terminal_run_state() -> None:
    terminal_payload = valid_event_payload()
    terminal_payload["id"] = "evt_terminal_marker"
    terminal_payload["run_id"] = "run_terminal_guard"
    terminal_payload["type"] = "summary"
    terminal_payload["requires_approval"] = False
    terminal_payload["approval"]["status"] = "not_required"
    terminal_payload["approval"]["requested_by"] = None
    terminal_payload["approval"]["resolved_by"] = None
    terminal_payload["approval"]["resolved_at"] = None
    terminal_payload["timestamp"] = "2026-02-14T13:00:00Z"
    assert client.post("/v1/events", json=terminal_payload).status_code == 201

    mutating_payload = valid_event_payload()
    mutating_payload["id"] = "evt_after_terminal_marker"
    mutating_payload["run_id"] = "run_terminal_guard"
    mutating_payload["type"] = "action"
    mutating_payload["requires_approval"] = False
    mutating_payload["approval"]["status"] = "not_required"
    mutating_payload["approval"]["requested_by"] = None
    mutating_payload["approval"]["resolved_by"] = None
    mutating_payload["approval"]["resolved_at"] = None
    mutating_payload["timestamp"] = "2026-02-14T13:00:01Z"

    response = client.post("/v1/events", json=mutating_payload)

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["details"] == [
        {
            "path": "workflow_status",
            "message": "event stream continued after terminal status 'completed'",
            "type": "state_conflict",
            "code": "TERMINAL_STATE_CONFLICT",
            "rule_id": "RULE-GATE-005",
        }
    ]
