from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tasks" / "branch_hygiene_inventory.sh"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue62_round1_branch_hygiene_script_exists_and_reports_dry_run_contract() -> None:
    result = _run_script("--help")

    assert result.returncode == 0
    assert "branch hygiene inventory" in result.stdout.lower()
    assert "dry-run only" in result.stdout.lower()


def test_issue62_round2_inventory_output_contains_required_sections() -> None:
    result = _run_script()

    assert result.returncode == 0
    assert "Branch Hygiene Inventory Snapshot" in result.stdout
    assert "Merged into origin/main" in result.stdout
    assert "Not merged into origin/main" in result.stdout
    assert "Deletion command template (operator-confirmed only)" in result.stdout


def test_issue62_round3_deletion_candidates_exclude_protected_refs() -> None:
    result = _run_script()

    assert result.returncode == 0
    deletion_section = result.stdout.split(
        "Deletion command template (operator-confirmed only)", maxsplit=1
    )[-1]
    assert "origin/main" not in deletion_section
    assert "origin/HEAD" not in deletion_section


def test_issue62_round4_default_mode_does_not_execute_remote_deletions() -> None:
    result = _run_script()

    assert result.returncode == 0
    assert (
        "git push origin --delete" in result.stdout
        or "No deletion candidates found." in result.stdout
    )
    assert "Executed remote deletion" not in result.stdout


def test_issue62_round5_repo_hygiene_docs_include_operational_command_and_issue_link() -> None:
    policy = (ROOT / "docs" / "REPO_HYGIENE.md").read_text(encoding="utf-8")
    snapshot = (ROOT / "docs" / "artifacts" / "issue-62" / "branch_inventory_snapshot.md").read_text(
        encoding="utf-8"
    )

    assert "SI-62B (#89)" in policy
    assert "bash tasks/branch_hygiene_inventory.sh" in policy
    assert "operator-confirmed" in policy
    assert "#62" in snapshot
