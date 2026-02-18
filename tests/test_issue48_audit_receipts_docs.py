from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_issue48_sub_issue_artifact_exists_with_expected_sections() -> None:
    sub_issues = _read("docs/artifacts/issue-48/sub_issues.md")
    assert "Issue #48 Sub-Issue Breakdown" in sub_issues
    assert "Sub-issue A" in sub_issues
    assert "Sub-issue E" in sub_issues


def test_issue48_api_docs_include_decision_audit_export_contract() -> None:
    api = _read("spec/API.md")
    assert "## GET /v1/approvals/decisions/{decision_id}/audit-export" in api
    assert "prev_hash" in api
    assert "hash" in api


def test_issue48_event_schema_docs_define_integrity_fields() -> None:
    schema = _read("spec/EVENT_SCHEMA.md")
    assert "hash" in schema
    assert "prev_hash" in schema


def test_issue48_business_rules_include_hash_chain_integrity_rule() -> None:
    rules = _read("spec/BUSINESS_RULES.md")
    assert "RULE-CORE-010" in rules
    assert "HASH_CHAIN_BROKEN" in rules


def test_issue48_readme_docs_include_audit_export_flow() -> None:
    readme = _read("README.md")
    assert "## Audit Export Flow (Issue #48)" in readme
    assert "GET /v1/approvals/decisions/{decision_id}/audit-export" in readme
    assert "hash" in readme
    assert "prev_hash" in readme


def test_issue48_gap_assessment_artifact_exists() -> None:
    gap = _read("docs/artifacts/issue-48/gap_assessment.md")
    assert "Issue #48 Post-Implementation Gap Assessment" in gap
    assert "#49" in gap
    assert "#75" in gap
    assert "#76" in gap
    assert "#62" in gap
