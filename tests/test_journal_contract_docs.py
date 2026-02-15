from pathlib import Path
import re


def _load(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text()


def _section(markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    assert match is not None, f"Missing section: {heading}"
    return match.group(1)


def test_journal_contract_has_canonical_endpoint_heading() -> None:
    api_md = _load("spec/API.md")
    _section(api_md, "GET /v1/runs/{run_id}/journal")


def test_journal_contract_documents_response_shape_and_traceability() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")

    assert "run_id" in journal
    assert "entry_count" in journal
    assert "entries" in journal
    assert "event_id" in journal
    assert "payload_ref" in journal
    assert "approval_context" in journal


def test_journal_contract_documents_deterministic_ordering_and_tiebreak() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")
    normalized = journal.lower()

    assert "deterministic" in normalized
    assert "timestamp" in normalized
    assert "ascending" in normalized
    assert "append sequence" in normalized


def test_journal_contract_documents_error_semantics() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")

    assert "404" in journal and "RUN_NOT_FOUND" in journal
    assert "409" in journal and "INCONSISTENT_RUN_STATE" in journal
    assert "500" in journal and "STORAGE_READ_ERROR" in journal


def test_journal_contract_examples_and_issue_links_are_present() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")
    normalized = journal.lower()

    assert "pending approval flow" in normalized
    assert "post-resolution flow" in normalized
    assert "#5" in journal
    assert "#13" in journal
    assert "#15" in journal


def test_architecture_docs_define_representation_layer_ownership() -> None:
    architecture_md = _load("docs/ARCHITECTURE.md")
    normalized = architecture_md.lower()

    assert "journal projection ownership" in normalized
    assert "representation layer" in normalized
    assert "must not" in normalized
    assert "governance" in normalized
