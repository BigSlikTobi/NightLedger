from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_issue46_api_contract_docs_include_decision_id_approval_endpoints() -> None:
    api = _read("spec/API.md")
    assert "## POST /v1/approvals/requests" in api
    assert "## POST /v1/approvals/decisions/{decision_id}" in api
    assert "## GET /v1/approvals/decisions/{decision_id}" in api
    assert "## POST /v1/approvals/{event_id} (legacy compatibility)" in api


def test_issue46_event_schema_docs_include_approval_decision_id_field() -> None:
    schema = _read("spec/EVENT_SCHEMA.md")
    assert "approval.decision_id" in schema
    assert '"decision_id": "dec_..."' in schema


def test_issue46_sub_issue_artifact_exists_and_records_boundaries() -> None:
    artifact = _read("docs/artifacts/issue-46/sub_issues.md")
    assert "Issue #46 Sub-Issue Breakdown" in artifact
    assert "Sub-issue A" in artifact
    assert "Sub-issue D" in artifact


def test_issue46_business_rules_docs_include_decision_id_consistency_rule() -> None:
    rules = _read("spec/BUSINESS_RULES.md")
    assert "RULE-GATE-011" in rules
    assert "APPROVAL_DECISION_ID_MISMATCH" in rules
