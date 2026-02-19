from pathlib import Path


def _load(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_issue47_api_docs_include_execution_token_and_executor_endpoints() -> None:
    api = _load("spec/API.md")

    assert "## POST /v1/executors/purchase.create" in api
    assert "## POST /v1/approvals/decisions/{decision_id}/execution-token" in api
    assert "execution_token" in api
    assert "EXECUTION_TOKEN_MISSING" in api
    assert "EXECUTION_TOKEN_INVALID" in api
    assert "EXECUTION_TOKEN_EXPIRED" in api
    assert "EXECUTION_TOKEN_REPLAYED" in api


def test_issue47_readme_docs_include_executor_trust_boundary_flow() -> None:
    readme = _load("docs/TECHNICAL_GUIDE.md")

    assert "## Token-Gated Executor Flow (Issue #47)" in readme
    assert "POST /v1/executors/purchase.create" in readme
    assert "POST /v1/approvals/decisions/{decision_id}/execution-token" in readme
    assert "Authorization: Bearer" in readme


def test_issue47_sub_issue_breakdown_exists_with_scope_boundaries() -> None:
    sub_issues = _load("docs/artifacts/issue-47/sub_issues.md")

    assert "# Issue #47 Sub-Issue Breakdown" in sub_issues
    assert "Enforcement token verification only" in sub_issues
    assert "No tamper-evident hash chain work (issue #48)" in sub_issues
