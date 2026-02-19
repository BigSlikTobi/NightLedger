from pathlib import Path


def _read(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_issue49_readme_documents_real_bot_mcp_plus_http_workflow() -> None:
    readme = _read("docs/TECHNICAL_GUIDE.md")
    normalized = readme.lower()

    assert "real bot" in normalized
    assert "mcp + http" in normalized
    assert "requires_approval" in normalized
    assert "/v1/approvals/requests" in readme
    assert "/v1/approvals/decisions/{decision_id}" in readme


def test_issue49_api_spec_defines_pause_wait_resume_contract() -> None:
    api = _read("spec/API.md")
    normalized = api.lower()

    assert "bot pause/wait/resume contract (issue #49 v1)" in normalized
    assert "allow => proceed" in normalized
    assert "requires_approval => pause" in normalized
    assert "deny => abort" in normalized
    assert "polling defaults" in normalized
    assert "interval: 2s" in normalized
    assert "timeout: 300s" in normalized


def test_issue49_docs_describe_ui_approval_then_bot_polling_resume() -> None:
    demo = _read("docs/DEMO_SCRIPT.md")
    api_testing = _read("docs/API_TESTING.md")

    assert "real bot workflow (issue #49 v1)" in demo.lower()
    assert "user approves/rejects in ui" in demo.lower()
    assert "bot polls get /v1/approvals/decisions/{decision_id}" in demo.lower()

    assert "real bot workflow (issue #49 v1)" in api_testing.lower()
    assert "post /v1/approvals/requests" in api_testing.lower()
    assert "get /v1/approvals/decisions/{decision_id}" in api_testing.lower()


def test_issue49_openclaw_workflow_artifact_exists_and_is_human_readable() -> None:
    artifact = _read("docs/artifacts/issue-49/openclaw_real_workflow.md")
    normalized = artifact.lower()

    assert "# issue #49 openclaw real workflow" in normalized
    assert "step 1" in normalized
    assert "step 8" in normalized
    assert "no simulation" in normalized
    assert "mcp decision" in normalized
    assert "human approval" in normalized


def test_issue49_gap_assessment_mentions_real_bot_contract_and_remaining_scope() -> None:
    gap = _read("docs/artifacts/issue-49/gap_assessment.md")
    normalized = gap.lower()

    assert "real bot workflow" in normalized
    assert "mcp + http" in normalized
    assert "#62" in gap
    assert "dynamic business rules" in normalized


def test_issue49_diary_records_real_bot_workflow_delivery() -> None:
    diary = _read("docs/diary.md")
    normalized = diary.lower()

    assert "issue #49" in normalized
    assert "real bot workflow" in normalized
    assert "polling" in normalized
    assert "pytest -q" in diary
