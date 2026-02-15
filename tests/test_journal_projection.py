from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.models.event_schema import EventPayload  # noqa: E402
from nightledger_api.services.event_store import InMemoryAppendOnlyEventStore  # noqa: E402
from nightledger_api.services.event_store import StoredEvent  # noqa: E402
from nightledger_api.services.journal_projection_service import project_run_journal  # noqa: E402


def test_round1_projection_fixture_maps_event_types_and_traceability() -> None:
    run_id, events = _happy_path_run_fixture()

    projection = project_run_journal(run_id=run_id, events=events).to_dict()

    assert [entry["event_type"] for entry in projection["entries"]] == [
        "intent",
        "action",
        "observation",
        "decision",
        "summary",
    ]

    for entry in projection["entries"]:
        payload_ref = entry["payload_ref"]
        assert payload_ref["run_id"] == run_id
        assert payload_ref["event_id"] == entry["event_id"]
        assert payload_ref["path"] == f"/v1/runs/{run_id}/events#{entry['event_id']}"


def test_round2_projection_fixture_is_deterministic_for_out_of_order_ingestion() -> None:
    first = _projected_entry_ids_for_out_of_order_ingestion()
    second = _projected_entry_ids_for_out_of_order_ingestion()

    assert first == ["evt_order_2", "evt_order_1", "evt_order_3"]
    assert second == first


def test_round3_projection_fixture_is_deterministic_for_same_timestamp_ties() -> None:
    first = _projected_entry_ids_for_same_timestamp_ties()
    second = _projected_entry_ids_for_same_timestamp_ties()

    assert first == ["evt_tie_1", "evt_tie_2", "evt_tie_3"]
    assert second == first


def test_round4_projection_fixture_renders_approval_pending_and_resolved_entries() -> None:
    projection = _approval_flow_fixture_projection()

    pending_entry = projection["entries"][1]
    resolved_entry = projection["entries"][2]

    assert pending_entry["event_type"] == "approval_requested"
    assert pending_entry["approval_context"]["requires_approval"] is True
    assert pending_entry["approval_context"]["status"] == "pending"
    assert pending_entry["approval_indicator"] == {
        "is_approval_required": True,
        "is_approval_resolved": False,
        "decision": None,
    }

    assert resolved_entry["event_type"] == "approval_resolved"
    assert resolved_entry["approval_context"]["requires_approval"] is True
    assert resolved_entry["approval_context"]["status"] == "approved"
    assert resolved_entry["approval_context"]["resolved_by"] == "human_reviewer"
    assert resolved_entry["approval_context"]["resolved_at"] == "2026-02-20T12:02:00Z"
    assert resolved_entry["approval_indicator"] == {
        "is_approval_required": True,
        "is_approval_resolved": True,
        "decision": "approved",
    }


def test_round5_projection_edge_fixture_preserves_evidence_and_raw_linkage() -> None:
    run_id, projection = _edge_path_projection_fixture()
    entries = projection["entries"]

    assert [entry["event_id"] for entry in entries] == [
        "evt_edge_older_pending",
        "evt_edge_newer_action",
        "evt_edge_resolved_rejected",
    ]

    for entry in entries:
        payload_ref = entry["payload_ref"]
        assert payload_ref["run_id"] == run_id
        assert payload_ref["event_id"] == entry["event_id"]
        assert payload_ref["path"] == f"/v1/runs/{run_id}/events#{entry['event_id']}"
        assert entry["evidence_refs"] == [
            {
                "kind": "log",
                "label": "Event log",
                "ref": f"log://{entry['event_id']}",
            }
        ]

    assert entries[0]["metadata"]["integrity_warning"] is True
    assert entries[2]["approval_context"]["status"] == "rejected"
    assert entries[2]["approval_indicator"] == {
        "is_approval_required": True,
        "is_approval_resolved": True,
        "decision": "rejected",
    }


def _happy_path_run_fixture() -> tuple[str, list[StoredEvent]]:
    run_id = "run_proj_happy"
    return (
        run_id,
        [
            _stored_event(
                event_id="evt_happy_1",
                run_id=run_id,
                timestamp="2026-02-20T09:00:00Z",
                event_type="intent",
                title="Plan transfer",
                details="Agent planned a low-risk transfer.",
            ),
            _stored_event(
                event_id="evt_happy_2",
                run_id=run_id,
                timestamp="2026-02-20T09:01:00Z",
                event_type="action",
                title="Validate source account",
                details="Agent validated account balance.",
            ),
            _stored_event(
                event_id="evt_happy_3",
                run_id=run_id,
                timestamp="2026-02-20T09:02:00Z",
                event_type="observation",
                title="Observed policy",
                details="Policy check returned pass.",
            ),
            _stored_event(
                event_id="evt_happy_4",
                run_id=run_id,
                timestamp="2026-02-20T09:03:00Z",
                event_type="decision",
                title="Proceed",
                details="Agent selected execution path A.",
            ),
            _stored_event(
                event_id="evt_happy_5",
                run_id=run_id,
                timestamp="2026-02-20T09:04:00Z",
                event_type="summary",
                title="Run summary",
                details="Workflow completed successfully.",
            ),
        ],
    )


def _stored_event(
    *,
    event_id: str,
    run_id: str,
    timestamp: str,
    event_type: str,
    title: str,
    details: str,
) -> StoredEvent:
    return StoredEvent(
        id=event_id,
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        run_id=run_id,
        payload={
            "id": event_id,
            "run_id": run_id,
            "timestamp": timestamp,
            "type": event_type,
            "actor": "agent",
            "title": title,
            "details": details,
            "confidence": 0.82,
            "risk_level": "low",
            "requires_approval": False,
            "approval": {
                "status": "not_required",
                "requested_by": None,
                "resolved_by": None,
                "resolved_at": None,
                "reason": None,
            },
            "evidence": [{"kind": "log", "label": "Event log", "ref": f"log://{event_id}"}],
        },
        integrity_warning=False,
    )


def _projected_entry_ids_for_out_of_order_ingestion() -> list[str]:
    run_id = "run_proj_order"
    store = InMemoryAppendOnlyEventStore()

    store.append(
        _event_payload(
            event_id="evt_order_1",
            run_id=run_id,
            timestamp="2026-02-20T10:01:00Z",
            event_type="action",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_order_2",
            run_id=run_id,
            timestamp="2026-02-20T10:00:00Z",
            event_type="observation",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_order_3",
            run_id=run_id,
            timestamp="2026-02-20T10:02:00Z",
            event_type="summary",
        )
    )

    projection = project_run_journal(run_id=run_id, events=store.list_by_run_id(run_id))
    return [entry.event_id for entry in projection.entries]


def _projected_entry_ids_for_same_timestamp_ties() -> list[str]:
    run_id = "run_proj_ties"
    store = InMemoryAppendOnlyEventStore()

    for event_id in ("evt_tie_1", "evt_tie_2", "evt_tie_3"):
        store.append(
            _event_payload(
                event_id=event_id,
                run_id=run_id,
                timestamp="2026-02-20T11:00:00Z",
                event_type="action",
            )
        )

    projection = project_run_journal(run_id=run_id, events=store.list_by_run_id(run_id))
    return [entry.event_id for entry in projection.entries]


def _event_payload(
    *,
    event_id: str,
    run_id: str,
    timestamp: str,
    event_type: str,
    requires_approval: bool = False,
    approval_status: str = "not_required",
    requested_by: str | None = None,
    resolved_by: str | None = None,
    resolved_at: str | None = None,
    reason: str | None = None,
) -> EventPayload:
    return EventPayload(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=event_type,
        actor="agent",
        title=f"{event_type} title",
        details=f"{event_type} details",
        confidence=0.8,
        risk_level="high" if requires_approval else "low",
        requires_approval=requires_approval,
        approval={
            "status": approval_status,
            "requested_by": requested_by,
            "resolved_by": resolved_by,
            "resolved_at": resolved_at,
            "reason": reason,
        },
        evidence=[{"kind": "log", "label": "Event log", "ref": f"log://{event_id}"}],
    )


def _approval_flow_fixture_projection() -> dict[str, object]:
    run_id = "run_proj_approval"
    store = InMemoryAppendOnlyEventStore()
    store.append(
        _event_payload(
            event_id="evt_appr_1",
            run_id=run_id,
            timestamp="2026-02-20T12:00:00Z",
            event_type="action",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_appr_2",
            run_id=run_id,
            timestamp="2026-02-20T12:01:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="transfer above policy threshold",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_appr_3",
            run_id=run_id,
            timestamp="2026-02-20T12:02:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="approved",
            requested_by="agent",
            resolved_by="human_reviewer",
            resolved_at="2026-02-20T12:02:00Z",
            reason="approved by reviewer",
        )
    )

    return project_run_journal(run_id=run_id, events=store.list_by_run_id(run_id)).to_dict()


def _edge_path_projection_fixture() -> tuple[str, dict[str, object]]:
    run_id = "run_proj_edge"
    store = InMemoryAppendOnlyEventStore()
    store.append(
        _event_payload(
            event_id="evt_edge_newer_action",
            run_id=run_id,
            timestamp="2026-02-20T13:01:00Z",
            event_type="action",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_edge_older_pending",
            run_id=run_id,
            timestamp="2026-02-20T13:00:00Z",
            event_type="approval_requested",
            requires_approval=True,
            approval_status="pending",
            requested_by="agent",
            reason="high-risk transfer",
        )
    )
    store.append(
        _event_payload(
            event_id="evt_edge_resolved_rejected",
            run_id=run_id,
            timestamp="2026-02-20T13:02:00Z",
            event_type="approval_resolved",
            requires_approval=True,
            approval_status="rejected",
            requested_by="agent",
            resolved_by="human_reviewer",
            resolved_at="2026-02-20T13:02:00Z",
            reason="policy denied",
        )
    )

    projection = project_run_journal(run_id=run_id, events=store.list_by_run_id(run_id))
    return run_id, projection.to_dict()
