from pathlib import Path


def _demo_script() -> str:
    return (Path(__file__).resolve().parents[1] / "docs" / "DEMO_SCRIPT.md").read_text(
        encoding="utf-8"
    )


def test_issue54_round1_demo_script_defines_reproducible_command_path_with_expected_outputs() -> None:
    content = _demo_script()
    normalized = content.lower()

    assert "## Reproducible Command Path (Issue #54)" in content
    assert "bash tasks/reset_seed_triage_inbox_demo.sh" in content
    assert "curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/status" in content
    assert "curl -sS -X POST http://127.0.0.1:8001/v1/approvals/evt_triage_inbox_003" in content
    assert "Expected output" in content
    assert "status: \"paused\"" in normalized
    assert "status: \"completed\"" in normalized


def test_issue54_round2_demo_script_includes_troubleshooting_matrix() -> None:
    content = _demo_script()
    normalized = content.lower()

    assert "## Troubleshooting" in content
    assert "API did not become ready" in content
    assert "NO_PENDING_APPROVAL" in content
    assert "RUN_NOT_FOUND" in content
    assert "curl -sS http://127.0.0.1:8001/openapi.json" in content
    assert "what to check" in normalized


def test_issue54_round3_demo_script_contains_step_to_receipt_evidence_checklist() -> None:
    content = _demo_script()
    normalized = content.lower()

    assert "## Evidence Checklist" in content
    assert "| Step | Endpoint/Action | Receipt evidence to show |" in content
    assert "reset-seed" in normalized
    assert "approval_requested" in normalized
    assert "approval_resolved" in normalized
    assert "evt_triage_inbox_004" in content
    assert "evt_triage_inbox_005" in content


def test_issue54_round4_demo_script_contains_operator_handoff_gates() -> None:
    content = _demo_script()
    normalized = content.lower()

    assert "## Operator Handoff" in content
    assert "Go/No-Go" in content
    assert "teammate execution checklist" in normalized
    assert "within_target" in content
    assert "run_status: \"completed\"" in content


def test_issue54_round5_diary_records_demo_script_handoff_completion() -> None:
    diary = (Path(__file__).resolve().parents[1] / "docs" / "diary.md").read_text(
        encoding="utf-8"
    )
    normalized = diary.lower()

    assert "issue #54" in normalized
    assert "reproducible demo script" in normalized
    assert "operator handoff" in normalized
    assert "pytest -q" in diary


def test_issue54_round6_demo_script_uses_persistent_api_then_seed_without_auto_start() -> None:
    content = _demo_script()

    assert "PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001" in content
    assert "AUTO_START=0 bash tasks/reset_seed_triage_inbox_demo.sh" in content
