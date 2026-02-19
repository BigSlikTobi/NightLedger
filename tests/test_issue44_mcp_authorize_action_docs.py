from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue44_readme_includes_mcp_authorize_action_examples() -> None:
    readme = _load("docs/TECHNICAL_GUIDE.md")

    assert "## MCP authorize_action (Issue #44 v1 contract)" in readme
    assert "POST /v1/mcp/authorize_action" in readme
    assert '"transport_decision_hint":"allow"' in readme
    assert '"transport_decision_hint":"deny"' in readme
    assert '"state":"allow"' in readme or '"state": "allow"' in readme
    assert '"state":"requires_approval"' in readme or '"state": "requires_approval"' in readme
    assert '"reason_code":"POLICY_ALLOW_WITHIN_THRESHOLD"' in readme or '"reason_code": "POLICY_ALLOW_WITHIN_THRESHOLD"' in readme
    assert '"reason_code":"AMOUNT_ABOVE_THRESHOLD"' in readme or '"reason_code": "AMOUNT_ABOVE_THRESHOLD"' in readme
    assert '"code":"REQUEST_VALIDATION_ERROR"' in readme or '"code": "REQUEST_VALIDATION_ERROR"' in readme
    assert '"code":"UNSUPPORTED_ACTION"' in readme or '"code": "UNSUPPORTED_ACTION"' in readme
    assert "### MCP stdio server wrapper" in readme
    assert "python -m nightledger_api.mcp_server" in readme


def test_issue44_api_spec_documents_decision_hint_defaults_and_error_code() -> None:
    api_spec = _load("spec/API.md")

    assert "context.transport_decision_hint" in api_spec
    assert "policy evaluation is authoritative for final decision" in api_spec
    assert '"state": "allow"' in api_spec
    assert '"state": "requires_approval"' in api_spec
    assert '"reason_code": "AMOUNT_ABOVE_THRESHOLD"' in api_spec
    assert '"code": "INVALID_TRANSPORT_DECISION_HINT"' in api_spec
    assert "## MCP stdio server: `authorize_action` tool" in api_spec
    assert "- `tools/call`" in api_spec
    assert "structuredContent" in api_spec
