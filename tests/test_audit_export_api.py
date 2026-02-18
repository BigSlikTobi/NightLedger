from pathlib import Path
from datetime import datetime, timezone
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.controllers.events_controller import get_event_store  # noqa: E402
from nightledger_api.main import app  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402
from nightledger_api.services.event_store import StoredEvent, _build_event_hash  # noqa: E402

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


def test_issue48_round3_audit_export_by_decision_id_returns_trace_with_hash_chain(monkeypatch) -> None:
    monkeypatch.setenv("NIGHTLEDGER_EXECUTION_TOKEN_SECRET", "issue48-round3-secret-material-32bytes!!")
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    run_id = "run_issue48_round3"
    authorize = client.post(
        "/v1/mcp/authorize_action",
        json=_authorize_payload(run_id=run_id, amount=100, request_id="req_issue48_round3"),
    )
    assert authorize.status_code == 200
    decision_id = authorize.json()["decision_id"]
    token = authorize.json()["execution_token"]

    execute = client.post(
        "/v1/executors/purchase.create",
        json={"run_id": run_id, "amount": 100, "currency": "EUR", "merchant": "ACME GmbH"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert execute.status_code == 200

    export = client.get(f"/v1/approvals/decisions/{decision_id}/audit-export")
    assert export.status_code == 200, export.json()
    body = export.json()

    assert body["decision_id"] == decision_id
    assert body["run_id"] == run_id
    assert body["event_count"] >= 3
    assert len(body["events"]) == body["event_count"]
    assert all(event["decision_id"] == decision_id for event in body["events"])
    assert any(event["action_type"] == "action" and event["reason"].startswith("decision_id=") for event in body["events"])
    assert body["events"][0]["prev_hash"] is None
    assert all(isinstance(event["hash"], str) and event["hash"].startswith("sha256:") for event in body["events"])


def test_issue48_round3_audit_export_unknown_decision_returns_structured_not_found() -> None:
    store = InMemoryAppendOnlyEventStore()
    app.dependency_overrides[get_event_store] = lambda: store

    response = client.get("/v1/approvals/decisions/dec_issue48_missing/audit-export")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "APPROVAL_NOT_FOUND"
    assert body["error"]["details"][0]["path"] == "decision_id"


class _TamperedDecisionTraceStore:
    def append(self, event: object) -> object:
        _ = event
        raise RuntimeError("append should not be called")

    def list_all(self) -> list[StoredEvent]:
        return [self._tampered_event()]

    def list_by_run_id(self, run_id: str) -> list[StoredEvent]:
        _ = run_id
        return [self._tampered_event()]

    def _tampered_event(self) -> StoredEvent:
        original_payload = {
            "id": "evt_issue48_tampered_1",
            "run_id": "run_issue48_tampered",
            "timestamp": "2026-02-18T17:00:00Z",
            "type": "decision",
            "actor": "system",
            "title": "authorize_action decision recorded",
            "details": "decision_id=dec_issue48_tampered state=allow",
            "confidence": 1.0,
            "risk_level": "low",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "decision_id": "dec_issue48_tampered",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [],
            "meta": {"workflow": "execution_gate", "step": "authorize_action"},
        }
        tampered_payload = dict(original_payload)
        tampered_payload["details"] = "decision_id=dec_issue48_tampered state=allow tampered=true"
        expected_hash = _build_event_hash(
            run_id="run_issue48_tampered",
            event_id="evt_issue48_tampered_1",
            timestamp="2026-02-18T17:00:00+00:00",
            payload=original_payload,
            integrity_warning=False,
            prev_hash=None,
        )
        return StoredEvent(
            id="evt_issue48_tampered_1",
            timestamp=datetime(2026, 2, 18, 17, 0, 0, tzinfo=timezone.utc),
            run_id="run_issue48_tampered",
            payload=tampered_payload,
            integrity_warning=False,
            prev_hash=None,
            hash=expected_hash,
        )


def test_issue48_round4_audit_export_rejects_tampered_payload_hash_mismatch() -> None:
    app.dependency_overrides[get_event_store] = lambda: _TamperedDecisionTraceStore()

    response = client.get("/v1/approvals/decisions/dec_issue48_tampered/audit-export")
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INCONSISTENT_RUN_STATE"
    assert body["error"]["details"][0]["code"] == "HASH_CHAIN_BROKEN"
