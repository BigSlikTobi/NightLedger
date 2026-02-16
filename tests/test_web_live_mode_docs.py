from pathlib import Path


def test_issue59_round4_web_readme_includes_copy_paste_live_mode_run_flow() -> None:
    readme = (Path(__file__).resolve().parents[1] / "apps" / "web" / "README.md").read_text(
        encoding="utf-8"
    )
    normalized = readme.lower()

    assert "## Live Mode (UI + API)" in readme
    assert "PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001" in readme
    assert "npm --prefix apps/web start" in readme
    assert "mode=live&runId=run_triage_inbox_demo_1&apiBase=http://127.0.0.1:8001" in readme
    assert "demo mode remains available" in normalized
