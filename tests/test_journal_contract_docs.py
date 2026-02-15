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


def test_round2_journal_endpoint_defines_response_shape_and_minimum_fields() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")

    assert "Response shape (v0 draft):" in journal
    assert "run_id" in journal
    assert "entry_count" in journal
    assert "entries" in journal
    assert "Minimum entry fields:" in journal
    assert "event_id" in journal
    assert "payload_ref" in journal
    assert "approval_context" in journal


def test_round3_journal_endpoint_defines_deterministic_order_and_tiebreak() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")
    normalized = journal.lower()

    assert "deterministic projection semantics:" in normalized
    assert "timestamp" in normalized and "ascending" in normalized
    assert "append sequence" in normalized
