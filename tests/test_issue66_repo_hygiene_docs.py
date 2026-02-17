from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue66_round1_branch_inventory_and_cleanup_decision_are_documented() -> None:
    hygiene = _load("docs/REPO_HYGIENE.md")

    assert "## Branch Inventory Snapshot (2026-02-17)" in hygiene
    assert "origin/Coder/issue-33-journal-projection-tests" in hygiene
    assert "origin/Integration/triage_inbox_phase1" in hygiene
    assert "Execution status: deferred" in hygiene
    assert "git push origin --delete" in hygiene


def test_issue66_round2_retention_policy_has_naming_age_and_safety_rules() -> None:
    hygiene = _load("docs/REPO_HYGIENE.md")

    assert "## Branch Retention Policy" in hygiene
    assert "`Coder/` branches are short-lived issue branches." in hygiene
    assert "Delete merged remote branches within 7 days" in hygiene
    assert "Never delete `main`" in hygiene
    assert "Require ahead/behind check before deletion" in hygiene


def test_issue66_round3_generated_artifact_history_strategy_is_explicit() -> None:
    hygiene = _load("docs/REPO_HYGIENE.md")

    assert "## Generated Artifact History Strategy" in hygiene
    assert "Decision: keep git history as-is (no rewrite)." in hygiene
    assert "__pycache__/" in hygiene
    assert "*.py[cod]" in hygiene
    assert "history rewrite" in hygiene


def test_issue66_round4_gitignore_covers_daily_generated_python_artifacts() -> None:
    gitignore = _load(".gitignore")

    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert "*$py.class" in gitignore
    assert ".pytest_cache/" in gitignore


def test_issue66_round5_closure_tracking_and_diary_entry_exist() -> None:
    hygiene = _load("docs/REPO_HYGIENE.md")
    diary = _load("docs/diary.md").lower()

    assert "Closure track for cleanup umbrella #62" in hygiene
    assert "Issue #66" in hygiene
    assert "issue #66" in diary
    assert "repo hygiene" in diary
    assert "stale branch" in diary
