from pathlib import Path
import re


def _load(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text()


def _section(markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    assert match is not None, f"Missing section: {heading}"
    return match.group(1)


def test_round1_journal_endpoint_has_canonical_heading_and_behavior() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")

    assert "Behavior:" in journal
    assert "200 OK" in journal
    assert "404 Not Found" in journal and "RUN_NOT_FOUND" in journal
    assert "409 Conflict" in journal and "INCONSISTENT_RUN_STATE" in journal
    assert "500 Internal Server Error" in journal and "STORAGE_READ_ERROR" in journal
