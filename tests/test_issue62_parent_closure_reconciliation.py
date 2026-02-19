from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue62_round6_gap_assessment_maps_closed_scope_and_open_post_mvp_issues() -> None:
    gap = _load("docs/artifacts/issue-62/gap_assessment.md")

    assert "# Issue #62 Final Gap Assessment" in gap
    assert "#88" in gap
    assert "#89" in gap
    assert "#84" in gap
    assert "#85" in gap
    assert "#86" in gap
    assert "README update remains an explicit open point" in gap


def test_issue62_round7_diary_entry_records_parent_closure_work() -> None:
    diary = _load("docs/diary.md").lower()

    assert "issue #62" in diary
    assert "si-62a" in diary
    assert "si-62b" in diary
    assert "progress issue-link policy" in diary
    assert "branch hygiene inventory" in diary
