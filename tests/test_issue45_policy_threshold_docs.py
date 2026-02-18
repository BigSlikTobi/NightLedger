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
    assert "AMOUNT_ABOVE_THRESHOLD" in sub_issues


def test_issue45_api_spec_documents_policy_threshold_contract() -> None:
    api_spec = _load("spec/API.md")

    assert "Behavior (issue #45 policy threshold v1):" in api_spec
    assert "context.amount" in api_spec
    assert "context.currency" in api_spec
    assert "NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR" in api_spec
    assert "amount <= threshold" in api_spec
    assert "amount > threshold" in api_spec
    assert '"reason_code": "AMOUNT_ABOVE_THRESHOLD"' in api_spec
    assert '"reason_code": "POLICY_ALLOW_WITHIN_THRESHOLD"' in api_spec
    assert '"path": "context.amount"' in api_spec
    assert '"code": "MISSING_AMOUNT"' in api_spec
    assert '"path": "context.currency"' in api_spec
    assert '"code": "UNSUPPORTED_CURRENCY"' in api_spec


def test_issue45_readme_documents_policy_inputs_and_outcomes() -> None:
    readme = _load("README.md")

    assert "Policy rule (Issue #45 sub-issue 1):" in readme
    assert "amount\":100" in readme
    assert "amount\":101" in readme
    assert "\"currency\":\"EUR\"" in readme
    assert "transport_decision_hint" in readme
    assert "\"reason_code\":\"AMOUNT_ABOVE_THRESHOLD\"" in readme
    assert "\"reason_code\":\"POLICY_ALLOW_WITHIN_THRESHOLD\"" in readme
    assert "## Policy Threshold Operator Flow (Issue #45)" in readme
    assert "/v1/mcp/authorize_action" in readme
    assert "/v1/approvals/pending" in readme
