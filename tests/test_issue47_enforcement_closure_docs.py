from pathlib import Path


def _load(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_issue47_gap_assessment_exists_with_remaining_open_issue_analysis() -> None:
    gap = _load("docs/artifacts/issue-47/gap_assessment.md")

    assert "# Issue #47 Post-Implementation Gap Assessment" in gap
    assert "#48" in gap
    assert "#49" in gap
    assert "#75" in gap
    assert "#76" in gap
    assert "replay" in gap.lower()
    assert "secret rotation" in gap.lower()


def test_issue47_diary_entry_records_delivery_and_validation_evidence() -> None:
    diary = _load("docs/diary.md").lower()

    assert "issue #47" in diary
    assert "token-gated" in diary
    assert "execution token" in diary
    assert "pytest -q" in diary
