from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tasks" / "validate_progress_issue_links.sh"


def _run_validator(target_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), str(target_root)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue62_round3_progress_validator_fails_on_unknown_reference(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    artifacts = docs / "artifacts" / "issue-99"
    artifacts.mkdir(parents=True)
    (docs / "diary.md").write_text("Progress update for #unknown\n", encoding="utf-8")
    (artifacts / "sub_issues.md").write_text("Parent issue: #99\n", encoding="utf-8")

    result = _run_validator(tmp_path)

    assert result.returncode != 0
    assert "Invalid issue placeholder" in result.stderr


def test_issue62_round3_progress_validator_passes_on_numeric_issue_references(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    artifacts = docs / "artifacts" / "issue-99"
    artifacts.mkdir(parents=True)
    (docs / "diary.md").write_text("Progress update mapped to #62\n", encoding="utf-8")
    (artifacts / "sub_issues.md").write_text("Child issue is #88\n", encoding="utf-8")
    (artifacts / "gap_assessment.md").write_text("Residuals tracked in #89\n", encoding="utf-8")

    result = _run_validator(tmp_path)

    assert result.returncode == 0
    assert "Validation passed" in result.stdout
