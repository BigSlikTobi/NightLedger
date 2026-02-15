from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore, StoredEvent  # noqa: E402

client = TestClient(app)


def build_event_payload(
    *,
    event_id: str,
    run_id: str,
    timestamp: str,
    event_type: str = "action",
    title: str = "Agent event",
    details: str = "Agent executed a workflow step.",
    requires_approval: bool = False,
    approval_status: str = "not_required",
    requested_by: str | None = None,
    resolved_by: str | None = None,
    resolved_at: str | None = None,
    reason: str | None = None,
    evidence: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": event_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "type": event_type,
        "actor": "agent",
        "title": title,
        "details": details,
        "confidence": 0.8,
        "risk_level": "high" if requires_approval else "low",
        "requires_approval": requires_approval,
        "approval": {
            "status": approval_status,
            "requested_by": requested_by,
            "resolved_by": resolved_by,
            "resolved_at": resolved_at,
            "reason": reason,
        },
        "evidence": evidence or [],
    }
    return payload


def ingest(payload: dict[str, Any]) -> None:
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 201, response.json()


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_round1_get_run_journal_returns_projection_for_known_run() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    ingest(
        build_event_payload(
            event_id="evt_journal_api_1",
            run_id="run_journal_api_1",
            timestamp="2026-02-17T14:00:00Z",
            title="Start transfer workflow",
            details="Agent initiated transfer",
            evidence=[
                {"kind": "log", "label": "Runtime log", "ref": "log://run/1001"},
            ],
        )
    )

    response = client.get("/v1/runs/run_journal_api_1/journal")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run_journal_api_1",
        "entry_count": 1,
        "entries": [
            {
                "entry_id": "jrnl_run_journal_api_1_0001",
                "event_id": "evt_journal_api_1",
                "timestamp": "2026-02-17T14:00:00Z",
                "event_type": "action",
                "title": "Start transfer workflow",
                "details": "Agent initiated transfer",
                "payload_ref": {
                    "run_id": "run_journal_api_1",
                    "event_id": "evt_journal_api_1",
                    "path": "/v1/runs/run_journal_api_1/events#evt_journal_api_1",
                },
                "approval_context": {
                    "requires_approval": False,
                    "status": "not_required",
                    "requested_by": None,
                    "resolved_by": None,
                    "resolved_at": None,
                    "reason": None,
                },
                "metadata": {
                    "actor": "agent",
                    "confidence": 0.8,
                    "risk_level": "low",
                    "integrity_warning": False,
                },
                "evidence_refs": [
                    {"kind": "log", "label": "Runtime log", "ref": "log://run/1001"},
                ],
            }
        ],
    }


def test_round2_get_run_journal_returns_not_found_for_unknown_run() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    response = client.get("/v1/runs/run_journal_unknown/journal")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RUN_NOT_FOUND"
    assert body["error"]["details"][0]["path"] == "run_id"


class _FailingJournalReadStore:
    def append(self, event: Any) -> Any:
        _ = event
        raise RuntimeError("append should not be called")

    def list_by_run_id(self, run_id: str) -> list[Any]:
        _ = run_id
        raise RuntimeError("unexpected backend failure")


def test_round3_get_run_journal_surfaces_storage_read_error() -> None:
    app.dependency_overrides[get_event_store] = lambda: _FailingJournalReadStore()

    response = client.get("/v1/runs/run_journal_fail/journal")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_READ_ERROR"
    assert body["error"]["details"][0]["code"] == "STORAGE_READ_FAILED"


class _InvalidTimestampJournalStore:
    def append(self, event: Any) -> Any:
        _ = event
        raise RuntimeError("append should not be called")

    def list_by_run_id(self, run_id: str) -> list[Any]:
        return [
            StoredEvent(
                id="evt_invalid_ts",
                timestamp="not-a-datetime",  # type: ignore[arg-type]
                run_id=run_id,
                payload={
                    "id": "evt_invalid_ts",
                    "run_id": run_id,
                    "timestamp": "2026-02-17T15:00:00Z",
                    "type": "action",
                    "actor": "agent",
                    "title": "Invalid timestamp source",
                    "details": "store returned malformed timestamp",
                    "confidence": 0.8,
                    "risk_level": "low",
                    "requires_approval": False,
                    "approval": {"status": "not_required"},
                    "evidence": [],
                },
                integrity_warning=False,
            )
        ]


def test_round4_get_run_journal_surfaces_inconsistent_state_for_invalid_timestamp() -> None:
    app.dependency_overrides[get_event_store] = lambda: _InvalidTimestampJournalStore()

    response = client.get("/v1/runs/run_invalid_ts/journal")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"][0]["path"] == "timestamp"
    assert body["error"]["details"][0]["code"] == "INVALID_EVENT_TIMESTAMP"
