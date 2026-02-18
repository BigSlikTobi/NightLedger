from pathlib import Path
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue76_sub_issue_artifact_exists_with_expected_sections() -> None:
    sub_issues = _read("docs/artifacts/issue-76/sub_issues.md")
    assert "Issue #76 Sub-Issue Breakdown" in sub_issues
    assert "Sub-issue A" in sub_issues
    assert "Sub-issue E" in sub_issues


def test_issue76_readme_documents_adoption_quickstart_and_demo_window() -> None:
    readme = _read("README.md")
    assert "## Adoption v1 Quickstart (Issue #76)" in readme
    assert "bash tasks/bootstrap_nightledger_runtime.sh" in readme
    assert "under 10 minutes" in readme
    assert "API + MCP" in readme


def test_issue76_api_spec_documents_authorize_action_contract_versioning_policy() -> None:
    api = _read("spec/API.md")
    assert "## authorize_action contract versioning policy" in api
    assert "contract_version" in api
    assert "backward-compatible" in api
    assert "deprecation" in api


def test_issue76_bootstrap_script_exists_and_is_executable() -> None:
    script = ROOT / "tasks" / "bootstrap_nightledger_runtime.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)


def test_issue76_bootstrap_script_dry_run_includes_api_and_mcp_start_commands() -> None:
    script = ROOT / "tasks" / "bootstrap_nightledger_runtime.sh"
    completed = subprocess.run(
        [str(script), "--dry-run"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert completed.returncode == 0, completed.stderr
    output = completed.stdout
    assert "nightledger_api.main:app" in output
    assert "nightledger_api.mcp_remote_server:app" in output
    assert "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN" in output


def test_issue76_readme_includes_local_stdio_and_remote_client_config_examples() -> None:
    readme = _read("README.md")
    assert "Claude Desktop (local stdio)" in readme
    assert '"command": "/Users/' in readme
    assert "nightledger_api.mcp_server" in readme
    assert "OpenHands/Cline-style (remote HTTP MCP)" in readme
    assert '"url": "http://<server-ip>:8002/v1/mcp/remote"' in readme
    assert '"MCP-Protocol-Version": "2025-06-18"' in readme


def test_issue76_readme_includes_under_10_minute_demo_flow() -> None:
    readme = _read("README.md")
    assert "## Adoption v1 demo flow (under 10 minutes)" in readme
    assert "bootstrap_nightledger_runtime.sh" in readme
    assert '"method":"initialize"' in readme
    assert '"method":"tools/list"' in readme
    assert '"method":"tools/call"' in readme


def test_issue76_gap_assessment_artifact_exists_with_open_issue_mapping() -> None:
    gap = _read("docs/artifacts/issue-76/gap_assessment.md")
    assert "Issue #76 Post-Implementation Gap Assessment" in gap
    assert "#49" in gap
    assert "#62" in gap


def test_issue76_diary_entry_exists() -> None:
    diary = _read("docs/diary.md")
    assert "Issue #76" in diary
    assert "adoption-ready" in diary
