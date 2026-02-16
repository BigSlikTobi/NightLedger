from pathlib import Path


def test_round5_api_testing_docs_include_single_command_demo_setup() -> None:
    docs_path = Path(__file__).resolve().parents[1] / "docs" / "API_TESTING.md"
    content = docs_path.read_text(encoding="utf-8")

    assert "bash tasks/reset_seed_triage_inbox_demo.sh" in content
