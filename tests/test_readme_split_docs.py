from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_split_round1_readme_is_visionary_and_links_technical_guide() -> None:
    readme = _load("README.md")

    assert "## Hackathon Narrative (Last 5 Days)" in readme
    assert "## Deconstructing Vision and MVP for Readers" in readme
    assert "docs/TECHNICAL_GUIDE.md" in readme


def test_readme_split_round2_readme_does_not_inline_full_transport_contracts() -> None:
    readme = _load("README.md")

    assert "## MCP authorize_action (Issue #44 v1 contract)" not in readme
    assert "### MCP remote server wrapper" not in readme


def test_readme_split_round3_technical_guide_contains_transport_and_enforcement_details() -> None:
    guide = _load("docs/TECHNICAL_GUIDE.md")

    assert "## MCP authorize_action (Issue #44 v1 contract)" in guide
    assert "### MCP remote server wrapper" in guide
    assert "## Token-Gated Executor Flow (Issue #47)" in guide
    assert "## Audit Export Flow (Issue #48)" in guide
