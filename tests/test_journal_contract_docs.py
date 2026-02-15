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


def test_round4_journal_endpoint_includes_explicit_error_envelope_examples() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")

    assert "Unknown run error response (v0 draft):" in journal
    assert "Inconsistent state error response (v0 draft):" in journal
    assert "Storage read error response (v0 draft):" in journal
    assert "\"error\"" in journal
    assert "\"details\"" in journal


def test_round5_journal_endpoint_includes_flow_examples_and_issue_links() -> None:
    api_md = _load("spec/API.md")
    journal = _section(api_md, "GET /v1/runs/{run_id}/journal")
    normalized = journal.lower()

    assert "pending approval flow" in normalized
    assert "post-resolution flow" in normalized
    assert "#5" in journal
    assert "#13" in journal
    assert "#15" in journal


def test_round5_architecture_docs_define_journal_representation_ownership() -> None:
    architecture_md = _load("docs/ARCHITECTURE.md")
    normalized = architecture_md.lower()

    assert "journal projection ownership" in normalized
    assert "representation layer" in normalized
    assert "must not" in normalized
    assert "governance" in normalized


def test_round1_api_testing_docs_include_journal_endpoint_curl_flow() -> None:
    api_testing_md = _load("docs/API_TESTING.md")
    normalized = api_testing_md.lower()

    assert "journal endpoint smoke flow (issue #35)" in normalized
    assert "curl -ss http://127.0.0.1:8001/v1/runs/run_approval_demo_1/journal" in normalized
    assert "curl -ss http://127.0.0.1:8001/v1/runs/run_journal_unknown/journal" in normalized


def test_round2_api_testing_docs_define_journal_response_fields() -> None:
    api_testing_md = _load("docs/API_TESTING.md")
    normalized = api_testing_md.lower()

    assert "entry_id" in normalized
    assert "payload_ref" in normalized
    assert "approval_context" in normalized
    assert "metadata" in normalized
    assert "evidence_refs" in normalized
    assert "approval_indicator" in normalized


def test_round3_api_testing_docs_capture_journal_error_behavior() -> None:
    api_testing_md = _load("docs/API_TESTING.md")
    normalized = api_testing_md.lower()

    assert "404 run_not_found" in normalized
    assert "409 inconsistent_run_state" in normalized
    assert "500 storage_read_error" in normalized


def test_round4_demo_script_calls_out_journal_readability_and_traceability() -> None:
    demo_script_md = _load("docs/DEMO_SCRIPT.md")
    normalized = demo_script_md.lower()

    assert "journal readability demo" in normalized
    assert "evidence traceability demo" in normalized
    assert "/v1/runs/{run_id}/journal" in demo_script_md


def test_round5_demo_script_includes_before_and_after_approval_journal_checks() -> None:
    demo_script_md = _load("docs/DEMO_SCRIPT.md")
    normalized = demo_script_md.lower()

    assert "before approval resolution" in normalized
    assert "after approval resolution" in normalized
    assert "approval_indicator" in normalized
