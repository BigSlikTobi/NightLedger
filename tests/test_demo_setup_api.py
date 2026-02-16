from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from nightledger_api.main import app  # noqa: E402


client = TestClient(app)


def test_round1_demo_reset_seed_returns_deterministic_manifest() -> None:
    response = client.post("/v1/demo/triage_inbox/reset-seed")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "seeded",
        "workflow": "triage_inbox",
        "run_id": "run_triage_inbox_demo_1",
        "event_count": 3,
        "seeded_event_ids": [
            "evt_triage_inbox_001",
            "evt_triage_inbox_002",
            "evt_triage_inbox_003",
        ],
    }


def test_round2_single_command_setup_script_exists_and_is_executable() -> None:
    script = Path(__file__).resolve().parents[1] / "tasks" / "reset_seed_triage_inbox_demo.sh"
    assert script.exists()
    assert script.stat().st_mode & 0o111


def test_round3_logs_structured_setup_failure(monkeypatch, caplog) -> None:
    from nightledger_api.controllers import events_controller

    def _invalid_seed_payloads() -> list[dict[str, object]]:
        return [
            {
                "id": "evt_invalid_1",
                "run_id": "run_triage_inbox_demo_1",
                "timestamp": "2026-02-16T08:00:00Z",
                "type": "action",
                "title": "Broken fixture",
                "details": "Should trigger validation",
                "requires_approval": False,
                "approval": {
                    "status": "not_required",
                    "requested_by": None,
                    "resolved_by": None,
                    "resolved_at": None,
                    "reason": None,
                },
                "evidence": [],
            }
        ]

    monkeypatch.setattr(events_controller, "_triage_inbox_seed_payloads", _invalid_seed_payloads)

    response = client.post("/v1/demo/triage_inbox/reset-seed")

    assert response.status_code == 422
    assert any("demo_seed_failed" in record.message for record in caplog.records)


def test_round4_unexpected_seed_append_failure_returns_structured_storage_error(monkeypatch) -> None:
    from nightledger_api.controllers import events_controller

    class _FailingStore:
        def append(self, event: object) -> object:
            _ = event
            raise RuntimeError("append exploded")

        def list_by_run_id(self, run_id: str) -> list[object]:
            _ = run_id
            return []

        def list_all(self) -> list[object]:
            return []

    monkeypatch.setattr(events_controller, "_reset_event_store", lambda: _FailingStore())

    response = client.post("/v1/demo/triage_inbox/reset-seed")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "STORAGE_WRITE_ERROR"
