from pathlib import Path


def _read(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_issue49_sub_issue_artifact_exists_with_atomic_breakdown() -> None:
    artifact = _read("docs/artifacts/issue-49/sub_issues.md")

    assert "# Issue #49 Sub-Issue Breakdown" in artifact
    assert "Sub-issue A" in artifact
    assert "Sub-issue E" in artifact
    assert "one-command deterministic smoke script" in artifact.lower()


def test_issue49_readme_references_purchase_enforcement_demo_path() -> None:
    readme = _read("README.md")
    normalized = readme.lower()

    assert "issue #49" in normalized
    assert "tasks/smoke_purchase_enforcement_demo.sh" in readme
    assert "block -> approve -> execute" in normalized


def test_issue49_purchase_smoke_script_exists_with_required_flow_steps() -> None:
    script = _read("tasks/smoke_purchase_enforcement_demo.sh")
    normalized = script.lower()

    assert script.startswith("#!/usr/bin/env bash")
    assert "/v1/mcp/authorize_action" in script
    assert "/v1/executors/purchase.create" in script
    assert "/v1/approvals/requests" in script
    assert "/v1/approvals/decisions/" in script
    assert "/execution-token" in script
    assert "amount\":500" in script.replace(" ", "")
    assert "requires_approval" in normalized


def test_issue49_purchase_smoke_script_emits_deterministic_operator_proof_lines() -> None:
    script = _read("tasks/smoke_purchase_enforcement_demo.sh")

    assert "STEP 1 PASS: authorize_action returned requires_approval for 500 EUR" in script
    assert "STEP 2 PASS: purchase executor blocked without token" in script
    assert "STEP 3 PASS: execution token mint blocked before approval" in script
    assert "STEP 4 PASS: decision approved by human reviewer" in script
    assert "STEP 5 PASS: execution token minted after approval" in script
    assert "STEP 6 PASS: purchase executor succeeded with valid token" in script
    assert "purchase-enforcement demo: PASS" in script


def test_issue49_demo_script_adds_purchase_command_path_without_replacing_issue54() -> None:
    demo = _read("docs/DEMO_SCRIPT.md")
    normalized = demo.lower()

    assert "## Reproducible Command Path (Issue #54)" in demo
    assert "## Purchase Enforcement Command Path (Issue #49)" in demo
    assert "bash tasks/smoke_purchase_enforcement_demo.sh" in demo
    assert "requires_approval for 500 EUR" in demo
    assert "blocked without token" in normalized
    assert "token minted after approval" in normalized
    assert "executor succeeded with valid token" in normalized


def test_issue49_demo_script_contains_purchase_evidence_checklist() -> None:
    demo = _read("docs/DEMO_SCRIPT.md")
    normalized = demo.lower()

    assert "## Purchase Enforcement Evidence Checklist (Issue #49)" in demo
    assert "| Step | Endpoint/Action | Receipt evidence to show |" in demo
    assert "/v1/mcp/authorize_action" in demo
    assert "/v1/executors/purchase.create" in demo
    assert "/v1/approvals/decisions/{decision_id}/execution-token" in demo
    assert "block -> approve -> execute" in normalized


def test_issue49_purchase_verification_artifact_exists_with_proof_sequence() -> None:
    artifact = _read("docs/artifacts/issue-49/purchase_enforcement_verification.md")
    normalized = artifact.lower()

    assert "# Issue #49 Purchase Enforcement Verification Artifact" in artifact
    assert "step 1 pass: authorize_action returned requires_approval for 500 eur" in normalized
    assert "step 2 pass: purchase executor blocked without token" in normalized
    assert "step 6 pass: purchase executor succeeded with valid token" in normalized
    assert "decision_id" in normalized
    assert "execution_token" in normalized


def test_issue49_purchase_verification_artifact_includes_regenerate_command() -> None:
    artifact = _read("docs/artifacts/issue-49/purchase_enforcement_verification.md")

    assert "## Regenerate" in artifact
    assert "AUTO_START=0 bash tasks/smoke_purchase_enforcement_demo.sh" in artifact


def test_issue49_gap_assessment_exists_with_issue62_mapping_and_recommendations() -> None:
    gap = _read("docs/artifacts/issue-49/gap_assessment.md")
    normalized = gap.lower()

    assert "# Issue #49 Post-Implementation Gap Assessment" in gap
    assert "#62" in gap
    assert "what #49 closes now" in normalized
    assert "remaining outside #49 scope" in normalized
    assert "recommended next steps" in normalized


def test_issue49_api_testing_guide_references_purchase_enforcement_script() -> None:
    api_testing = _read("docs/API_TESTING.md")

    assert "## Purchase enforcement smoke flow (Issue #49)" in api_testing
    assert "bash tasks/smoke_purchase_enforcement_demo.sh" in api_testing
    assert "block -> approve -> execute" in api_testing.lower()


def test_issue49_diary_entry_records_delivery_validation_and_findings() -> None:
    diary = _read("docs/diary.md")
    normalized = diary.lower()

    assert "issue #49" in normalized
    assert "smoke_purchase_enforcement_demo.sh" in diary
    assert "gap assessment" in normalized
    assert "pytest -q" in diary
