from pathlib import Path


def test_round5_api_testing_docs_include_single_command_demo_setup() -> None:
    docs_path = Path(__file__).resolve().parents[1] / "docs" / "API_TESTING.md"
    content = docs_path.read_text(encoding="utf-8")

    assert "bash tasks/reset_seed_triage_inbox_demo.sh" in content


def test_issue53_round4_api_testing_docs_reference_integration_artifact_path() -> None:
    docs_path = Path(__file__).resolve().parents[1] / "docs" / "API_TESTING.md"
    content = docs_path.read_text(encoding="utf-8")
    normalized = content.lower()

    assert "integration verification artifacts (issue #53)" in normalized
    assert "docs/artifacts/issue-53/triage_inbox_verification.md" in content


def test_issue53_round5_verification_artifact_contains_timing_and_state_proof() -> None:
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "artifacts"
        / "issue-53"
        / "triage_inbox_verification.md"
    )
    assert artifact_path.exists()

    content = artifact_path.read_text(encoding="utf-8")
    normalized = content.lower()

    assert "run_triage_inbox_demo_1" in content
    assert "status: paused" in normalized
    assert "status: completed" in normalized
    assert "timing.target_ms" in content
    assert "orchestration_receipt_gap_ms" in content
    assert "state_transition" in content


def test_issue53_round6_artifact_defines_contract_assertions_and_refresh_path() -> None:
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "artifacts"
        / "issue-53"
        / "triage_inbox_verification.md"
    )
    content = artifact_path.read_text(encoding="utf-8")

    assert "## Contract assertions" in content
    assert "approval_to_state_update_ms <= timing.target_ms" in content
    assert "Regenerate with" in content
    assert "tasks/reset_seed_triage_inbox_demo.sh" in content
