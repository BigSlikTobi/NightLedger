from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue44_readme_includes_mcp_authorize_action_examples() -> None:
    readme = _load("docs/TECHNICAL_GUIDE.md")

    assert "## MCP authorize_action (v2 user-local rule engine)" in readme
    assert "POST /v1/mcp/authorize_action" in readme
    assert '"user_id":"user_123"' in readme
    assert '"state":"allow"' in readme or '"state": "allow"' in readme
    assert '"state":"requires_approval"' in readme or '"state": "requires_approval"' in readme
    assert '"reason_code":"POLICY_ALLOW_NO_MATCH"' in readme or '"reason_code": "POLICY_ALLOW_NO_MATCH"' in readme
    assert '"reason_code":"RULE_REQUIRE_APPROVAL"' in readme or '"reason_code": "RULE_REQUIRE_APPROVAL"' in readme
    assert '"code":"REQUEST_VALIDATION_ERROR"' in readme or '"code": "REQUEST_VALIDATION_ERROR"' in readme
    assert '"code":"MISSING_USER_ID"' in readme or '"code": "MISSING_USER_ID"' in readme
    assert "### MCP stdio server wrapper" in readme
    assert "python -m nightledger_api.mcp_server" in readme


def test_issue44_api_spec_documents_user_rule_contract_and_error_code() -> None:
    api_spec = _load("spec/API.md")

    assert "NIGHTLEDGER_USER_RULES_FILE" in api_spec
    assert "context.user_id" in api_spec
    assert '"state": "allow"' in api_spec
    assert '"state": "requires_approval"' in api_spec
    assert '"reason_code": "RULE_REQUIRE_APPROVAL"' in api_spec
    assert '"code": "MISSING_USER_ID"' in api_spec
    assert "## MCP stdio server: `authorize_action` tool" in api_spec
    assert "- `tools/call`" in api_spec
    assert "structuredContent" in api_spec
