from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue45_sub_issue_breakdown_is_documented_in_git() -> None:
    sub_issues = _load("docs/artifacts/issue-45/sub_issues.md")

    assert "# Issue #45 Sub-Issue Breakdown" in sub_issues
    assert "## Sub-issue 1 (completed in this branch)" in sub_issues
    assert "## Sub-issue 2 (completed in this branch)" in sub_issues
    assert "## Sub-issue 3 (completed in this branch)" in sub_issues


def test_issue45_api_spec_documents_user_local_rule_contract() -> None:
    api_spec = _load("spec/API.md")

    assert "Behavior (multi-action user-local rules v2):" in api_spec
    assert "context.user_id" in api_spec
    assert "context.amount" in api_spec
    assert "context.currency" in api_spec
    assert "NIGHTLEDGER_USER_RULES_FILE" in api_spec
    assert '"reason_code": "RULE_REQUIRE_APPROVAL"' in api_spec
    assert '"reason_code": "POLICY_ALLOW_NO_MATCH"' in api_spec
    assert '"code": "MISSING_USER_ID"' in api_spec
    assert '"code": "MISSING_RULE_INPUT"' in api_spec


def test_issue45_readme_documents_policy_inputs_and_outcomes() -> None:
    readme = _load("docs/TECHNICAL_GUIDE.md")

    assert "Policy rule inputs and source:" in readme
    assert "NIGHTLEDGER_USER_RULES_FILE" in readme
    assert '"user_id":"user_123"' in readme
    assert '"reason_code":"RULE_REQUIRE_APPROVAL"' in readme or '"reason_code": "RULE_REQUIRE_APPROVAL"' in readme
    assert '"reason_code":"POLICY_ALLOW_NO_MATCH"' in readme or '"reason_code": "POLICY_ALLOW_NO_MATCH"' in readme
    assert "/v1/mcp/authorize_action" in readme
    assert "/v1/approvals/pending" in readme
