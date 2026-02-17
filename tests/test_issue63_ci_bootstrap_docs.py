from pathlib import Path


def _ci_workflow() -> str:
    return (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")


def _root_readme() -> str:
    return (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def _diary() -> str:
    return (Path(__file__).resolve().parents[1] / "docs" / "diary.md").read_text(encoding="utf-8")


def test_issue63_round1_ci_runs_backend_regression_suite_with_deterministic_python_setup() -> None:
    content = _ci_workflow()

    assert "actions/setup-python@v5" in content
    assert "python-version: '3.11'" in content
    assert "python -m venv .venv" in content
    assert "./.venv/bin/pip install -r requirements.txt" in content
    assert "./.venv/bin/pytest -q" in content


def test_issue63_round2_ci_runs_web_test_command() -> None:
    content = _ci_workflow()

    assert "node --test model/*.test.js controller/*.test.js" in content


def test_issue63_round3_ci_is_not_placeholder_only_and_runs_on_push_and_pr() -> None:
    content = _ci_workflow()

    assert "placeholder" not in content.lower()
    assert 'echo "Wire lint/test commands after stack bootstrap"' not in content
    assert "on:" in content
    assert "push:" in content
    assert "pull_request:" in content
    assert "backend-tests:" in content
    assert "web-tests:" in content


def test_issue63_round4_readme_documents_canonical_local_verification_flow_matching_ci() -> None:
    readme = _root_readme()

    assert "## Local Verification (Matches CI)" in readme
    assert "python -m venv .venv" in readme
    assert "./.venv/bin/pip install --upgrade pip" in readme
    assert "./.venv/bin/pip install -r requirements.txt" in readme
    assert "./.venv/bin/pytest -q" in readme
    assert "cd apps/web" in readme
    assert "node --test model/*.test.js controller/*.test.js" in readme


def test_issue63_round5_diary_records_ci_and_fresh_clone_bootstrap_parity_work() -> None:
    diary = _diary().lower()

    assert "issue #63" in diary
    assert "real ci checks" in diary
    assert "fresh clone" in diary
    assert "./.venv/bin/pytest -q" in diary
    assert "node --test model/*.test.js controller/*.test.js" in diary
