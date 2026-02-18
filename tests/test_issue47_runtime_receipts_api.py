from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_store import (  # noqa: E402
    InMemoryAppendOnlyEventStore,
    SQLiteAppendOnlyEventStore,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()



def _authorize_payload(*, run_id: str, amount: int, request_id: str) -> dict[str, Any]:
    return {
        "intent": {"action": "purchase.create"},
        "context": {
            "run_id": run_id,
            "request_id": request_id,
            "amount": amount,
            "currency": "EUR",
            "merchant": "ACME GmbH",
        },
    }



def _exec_payload(*, run_id: str, amount: int = 100, merchant: str = "ACME GmbH") -> dict[str, Any]:
    return {
        "run_id": run_id,
        "amount": amount,
        "currency": "EUR",
        "merchant": merchant,
    }



def _journal(run_id: str) -> dict[str, Any]:
    response = client.get(f"/v1/runs/{run_id}/journal")
    assert response.status_code == 200, response.json()
    return response.json()



def test_issue47_round1_authorize_allow_appends_runtime_decision_and_token_receipts(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-round1-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue47_round1"
    response = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_round1"),
    )
    assert response.status_code == 200

    journal = _journal(run_id)
    titles = [entry["title"] for entry in journal["entries"]]
    assert "authorize_action decision recorded" in titles
    assert "execution token minted" in titles



def test_issue47_round2_execution_token_mint_by_decision_id_appends_receipt(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-round2-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue47_round2"
    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=500, request_id="req_round2"),
    )
    assert authorize.status_code == 200
    decision_id = authorize.json()["decision_id"]

    register = client.post(
        "/v1/approvals/requests",
        json={
            "decision_id": decision_id,
            "run_id": run_id,
            "requested_by": "agent",
            "title": "Approval required",
            "details": "Purchase amount exceeds threshold",
            "risk_level": "high",
            "reason": "Above threshold",
        },
    )
    assert register.status_code == 200

    resolve = client.post(
        f"/v1/approvals/decisions/{decision_id}",
        json={"decision": "approved", "approver_id": "human_reviewer"},
    )
    assert resolve.status_code == 200

    mint = client.post(
        f"/v1/approvals/decisions/{decision_id}/execution-token",
        json={"amount": 500, "currency": "EUR", "merchant": "ACME GmbH"},
    )
    assert mint.status_code == 200

    journal = _journal(run_id)
    assert any(
        entry["title"] == "execution token minted"
        and entry["event_type"] == "decision"
        for entry in journal["entries"]
    )



def test_issue47_round3_executor_success_and_blocked_paths_append_receipts(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-round3-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue47_round3"
    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_round3"),
    )
    assert authorize.status_code == 200
    token = authorize.json()["execution_token"]

    mismatch = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(run_id=run_id, amount=100, merchant="Mallory Corp"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mismatch.status_code == 403

    authorize_success = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_round3_success"),
    )
    assert authorize_success.status_code == 200
    success_token = authorize_success.json()["execution_token"]

    execute = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(run_id=run_id),
        headers={"Authorization": f"Bearer {success_token}"},
    )
    assert execute.status_code == 200

    journal = _journal(run_id)
    assert any(entry["event_type"] == "error" and "EXECUTION_PAYLOAD_MISMATCH" in entry["details"] for entry in journal["entries"])
    assert any(entry["event_type"] == "action" and entry["title"] == "purchase.create executed" for entry in journal["entries"])



def test_issue47_round4_sqlite_event_store_persists_events_between_instances(tmp_path) -> None:
    db_path = tmp_path / "runtime_events.db"
    store_one = SQLiteAppendOnlyEventStore(path=str(db_path))

    payload = {
        "id": "evt_issue47_round4_1",
        "run_id": "run_issue47_round4",
        "timestamp": "2026-02-18T12:00:00Z",
        "type": "decision",
        "actor": "system",
        "title": "persisted decision",
        "details": "sqlite persistence check",
        "confidence": 1.0,
        "risk_level": "low",
        "requires_approval": False,
        "approval": {
            "status": "not_required",
            "requested_by": None,
            "resolved_by": None,
            "resolved_at": None,
            "reason": None,
        },
        "evidence": [],
        "meta": {"workflow": "execution_gate", "step": "persistence_check"},
    }

    from nightledger_api.services.event_ingest_service import validate_event_payload

    store_one.append(validate_event_payload(payload))

    store_two = SQLiteAppendOnlyEventStore(path=str(db_path))
    events = store_two.list_by_run_id("run_issue47_round4")
    assert len(events) == 1
    assert events[0].id == "evt_issue47_round4_1"



def test_issue47_round5_journal_projection_exposes_execution_receipt_metadata_for_ui(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue47-round5-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue47_round5"
    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_round5"),
    )
    assert authorize.status_code == 200
    token = authorize.json()["execution_token"]

    execute = client.post(
        "/v1/executors/purchase.create",
        json=_exec_payload(run_id=run_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert execute.status_code == 200

    journal = _journal(run_id)
    execution_entries = [entry for entry in journal["entries"] if entry["title"] == "purchase.create executed"]
    assert execution_entries, journal
    execution = execution_entries[-1]
    assert execution["metadata"]["actor"] == "system"
    assert execution["event_type"] == "action"
    assert execution["payload_ref"]["path"].startswith(f"/v1/runs/{run_id}/events#")


def test_issue48_round1_runtime_receipt_persists_decision_id_link(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue48-round1-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue48_round1"
    response = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_issue48_round1"),
    )
    assert response.status_code == 200
    decision_id = response.json()["decision_id"]

    events_response = client.get(f"/v1/runs/{run_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    decision_receipts = [event for event in events if event["payload"]["title"] == "authorize_action decision recorded"]
    assert decision_receipts, events
    assert decision_receipts[-1]["payload"]["approval"]["decision_id"] == decision_id
