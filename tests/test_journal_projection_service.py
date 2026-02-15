from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.services.event_store import StoredEvent  # noqa: E402
from nightledger_api.services.journal_projection_service import project_run_journal  # noqa: E402


def _stored_event(
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
        },
        integrity_warning=False,
    )


def test_round1_project_run_journal_maps_baseline_readable_entry() -> None:
    projection = project_run_journal(
        run_id="run_journal_1",
        events=[
            _stored_event(
                event_id="evt_journal_1",
                run_id="run_journal_1",
                timestamp="2026-02-17T09:00:00Z",
                event_type="action",
                title="Start workflow",
                details="Agent started transfer workflow",
                requires_approval=False,
                approval_status="not_required",
            )
        ],
    )

    assert projection.to_dict() == {
        "run_id": "run_journal_1",
        "entry_count": 1,
        "entries": [
            {
                "entry_id": "jrnl_run_journal_1_0001",
                "event_id": "evt_journal_1",
                "timestamp": "2026-02-17T09:00:00Z",
                "event_type": "action",
                "title": "Start workflow",
                "details": "Agent started transfer workflow",
                "payload_ref": {
                    "run_id": "run_journal_1",
                    "event_id": "evt_journal_1",
                    "path": "/v1/runs/run_journal_1/events#evt_journal_1",
                },
                "approval_context": {
                    "requires_approval": False,
                    "status": "not_required",
                    "requested_by": None,
                    "resolved_by": None,
                    "resolved_at": None,
                    "reason": None,
                },
            }
        ],
    }


def test_round2_project_run_journal_includes_evidence_references() -> None:
    projection = project_run_journal(
        run_id="run_journal_evidence",
        events=[
            _stored_event(
                event_id="evt_journal_evidence",
                run_id="run_journal_evidence",
                timestamp="2026-02-17T10:00:00Z",
                event_type="observation",
                title="Collected evidence",
                details="Agent captured execution artifacts",
                evidence=[
                    {"kind": "log", "label": "Runtime log", "ref": "log://run/1"},
                    {
                        "kind": "artifact",
                        "label": "Output bundle",
                        "ref": "artifact://bundle/abc",
                    },
                ],
            )
        ],
    )

    body = projection.to_dict()
    assert body["entries"][0]["evidence_refs"] == [
        {"kind": "log", "label": "Runtime log", "ref": "log://run/1"},
        {"kind": "artifact", "label": "Output bundle", "ref": "artifact://bundle/abc"},
    ]


def test_round3_project_run_journal_surfaces_approval_transition_indicators() -> None:
    projection = project_run_journal(
        run_id="run_journal_approval",
        events=[
            _stored_event(
                event_id="evt_apr_req",
                run_id="run_journal_approval",
                timestamp="2026-02-17T11:00:00Z",
                event_type="approval_requested",
                title="Approval required",
                details="Transfer exceeds threshold",
                requires_approval=True,
                approval_status="pending",
                requested_by="agent",
                reason="Transfer exceeds threshold",
            ),
            _stored_event(
                event_id="evt_apr_res",
                run_id="run_journal_approval",
                timestamp="2026-02-17T11:01:00Z",
                event_type="approval_resolved",
                title="Approval resolved",
                details="Human approved transfer",
                requires_approval=True,
                approval_status="approved",
                requested_by="agent",
                resolved_by="human_reviewer",
                resolved_at="2026-02-17T11:01:00Z",
                reason="Within policy",
            ),
        ],
    ).to_dict()

    assert projection["entries"][0]["approval_indicator"] == {
        "is_approval_required": True,
        "is_approval_resolved": False,
        "decision": None,
    }
    assert projection["entries"][1]["approval_indicator"] == {
        "is_approval_required": True,
        "is_approval_resolved": True,
        "decision": "approved",
    }
