from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue62_round1_sub_issue_breakdown_exists_and_links_parent_and_children() -> None:
    content = _load("docs/artifacts/issue-62/sub_issues.md")

    assert "# Issue #62 Sub-Issue Breakdown" in content
    assert "Parent issue: #62" in content
    assert "SI-62A" in content
    assert "#88" in content
    assert "SI-62B" in content
    assert "#89" in content


def test_issue62_round2_pr_template_requires_linked_issue_reference() -> None:
    template = _load(".github/pull_request_template.md")

    assert "## Linked Issue" in template
    assert "#<number>" in template
    assert "#unknown" not in template.lower()
    assert "#tbd" not in template.lower()


def test_issue62_round4_ci_runs_progress_issue_link_validation() -> None:
    ci = _load(".github/workflows/ci.yml")

    assert "validate-progress-refs" in ci
    assert "bash tasks/validate_progress_issue_links.sh" in ci


def test_issue62_round5_progress_update_policy_documents_rule_and_command() -> None:
    policy = _load("docs/PROGRESS_UPDATE_POLICY.md")

    assert "# Progress Update Issue-Link Policy" in policy
    assert "Parent issue: #62" in policy
    assert "SI-62A (#88)" in policy
    assert "bash tasks/validate_progress_issue_links.sh" in policy
    assert "#unknown" in policy
    assert "#TBD" in policy
