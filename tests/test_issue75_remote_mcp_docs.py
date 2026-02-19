from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue75_sub_issue_artifact_exists_with_expected_sections() -> None:
    sub_issues = _load("docs/artifacts/issue-75/sub_issues.md")
    assert "Issue #75 Sub-Issue Breakdown" in sub_issues
    assert "Sub-issue A" in sub_issues
    assert "Sub-issue E" in sub_issues


def test_issue75_api_spec_documents_remote_mcp_transport_and_auth() -> None:
    api = _load("spec/API.md")
    assert "## MCP remote server: streamable HTTP `authorize_action` tool" in api
    assert "POST /v1/mcp/remote" in api
    assert "GET /v1/mcp/remote" in api
    assert "DELETE /v1/mcp/remote" in api
    assert "initialize" in api
    assert "tools/list" in api
    assert "tools/call" in api
    assert "Authorization: Bearer <token>" in api
    assert "X-API-Key: <token>" in api
    assert "MCP-Session-Id" in api
    assert "MCP-Protocol-Version" in api
    assert "NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS" in api
    assert "/.well-known/oauth-protected-resource" in api


def test_issue75_readme_includes_remote_mcp_operator_setup() -> None:
    readme = _load("docs/TECHNICAL_GUIDE.md")
    assert "### MCP remote server wrapper" in readme
    assert "nightledger_api.mcp_remote_server" in readme
    assert "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN" in readme
    assert "NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS" in readme
    assert "server machine" in readme
    assert "client machine" in readme
    assert "MCP-Session-Id" in readme
    assert "MCP-Protocol-Version" in readme


def test_issue75_gap_assessment_artifact_exists_with_open_issue_mapping() -> None:
    gap = _load("docs/artifacts/issue-75/gap_assessment.md")
    assert "Issue #75 Post-Implementation Gap Assessment" in gap
    assert "#76" in gap
    assert "#49" in gap
    assert "#62" in gap


def test_issue75_diary_entry_exists() -> None:
    diary = _load("docs/diary.md")
    assert "Issue #75" in diary
    assert "remote MCP transport" in diary
