from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue44_readme_includes_mcp_authorize_action_examples() -> None:
    readme = _load("README.md")

    assert "## MCP authorize_action (Issue #44 v1 contract)" in readme
    assert "POST /v1/mcp/authorize_action" in readme
    assert '"transport_decision_hint":"allow"' in readme
    assert '"transport_decision_hint":"requires_approval"' in readme
    assert '"transport_decision_hint":"deny"' in readme
    assert '"state":"allow"' in readme
    assert '"state":"requires_approval"' in readme
    assert '"state":"deny"' in readme
    assert '"code":"REQUEST_VALIDATION_ERROR"' in readme
    assert '"code":"UNSUPPORTED_ACTION"' in readme


def test_issue44_api_spec_documents_decision_hint_defaults_and_error_code() -> None:
    api_spec = _load("spec/API.md")

    assert "context.transport_decision_hint" in api_spec
    assert "Decision state defaults to `allow` when hint is omitted" in api_spec
    assert '"state": "allow"' in api_spec
    assert '"state": "requires_approval"' in api_spec
    assert '"state": "deny"' in api_spec
    assert '"code": "INVALID_TRANSPORT_DECISION_HINT"' in api_spec
