from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue45_handoff_doc_links_downstream_issue_boundaries() -> None:
    handoff = _load("docs/artifacts/issue-45/handoff.md")

    assert "# Issue #45 Downstream Handoff" in handoff
    assert "## Scenario Linkage" in handoff
    assert "120 EUR -> requires_approval" in handoff
    assert "80 EUR -> allow" in handoff
    assert "## Downstream Ownership" in handoff
    assert "| #46 |" in handoff
    assert "| #47 |" in handoff
    assert "| #49 |" in handoff
    assert "decision_id" in handoff
    assert "token-gated" in handoff
    assert "demo script" in handoff


def test_issue45_handoff_doc_defines_no_scope_overlap_constraints() -> None:
    handoff = _load("docs/artifacts/issue-45/handoff.md")

    assert "## Out of Scope in #45" in handoff
    assert "no decision_id approval resolution API" in handoff
    assert "no executor token verification" in handoff
    assert "no purchase demo orchestration script packaging" in handoff
