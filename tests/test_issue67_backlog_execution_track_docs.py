from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue67_round1_dependency_ordered_execution_track_exists() -> None:
    track = _load("docs/MCP_POLICY_EXECUTION_TRACK.md")

    assert "# MCP + Policy Execution Track (Issue #67)" in track
    assert "## Dependency-Ordered Phases" in track
    assert "Phase 1: MCP transport contract (#44)" in track
    assert "Phase 2: policy evaluation rule (#45)" in track
    assert "Phase 3: human approval flow (#46)" in track
    assert "Phase 4: runtime enforcement boundary (#47)" in track
    assert "Phase 5: append-only audit receipts (#48)" in track
    assert "Phase 6: deterministic demo proof path (#49)" in track
    assert "Historical dependency anchor: #12" in track
    assert "Historical dependency anchor: #13" in track


def test_issue67_round2_retained_issues_define_non_overlapping_scope_and_done_criteria() -> None:
    track = _load("docs/MCP_POLICY_EXECUTION_TRACK.md")

    assert "## Retained Issue Boundaries" in track
    assert "| #44 | Transport contract only |" in track
    assert "| #45 | Policy evaluation only |" in track
    assert "| #46 | Approval state transition only |" in track
    assert "| #47 | Enforcement token verification only |" in track
    assert "| #48 | Audit receipt integrity only |" in track
    assert "| #49 | Demo orchestration only |" in track
    assert "Done criteria:" in track
    assert "No retained issue owns another issue's primary deliverable." in track


def test_issue67_round3_user_defined_rule_acceptance_criteria_include_threshold_example() -> None:
    track = _load("docs/MCP_POLICY_EXECUTION_TRACK.md")

    assert "## User-Defined Rule Acceptance Criteria" in track
    assert "Threshold example (v1): purchase.amount > 100 EUR -> requires_approval" in track
    assert "Policy input contract includes action type, currency, and numeric amount." in track
    assert "Boundary expectations: 100 EUR => allow, 101 EUR => requires_approval." in track
    assert "Decision includes reason code: AMOUNT_ABOVE_THRESHOLD." in track


def test_issue67_round4_mcp_integration_boundaries_are_explicit() -> None:
    track = _load("docs/MCP_POLICY_EXECUTION_TRACK.md")

    assert "## MCP Integration Boundaries" in track
    assert "| NightLedger ownership | External ownership |" in track
    assert "| authorize_action contract validation and decision_id issuance | agent tool invocation wiring and retries |" in track
    assert "| policy evaluation and approval state machine | business-side action execution (purchase processor) |" in track
    assert "| append-only receipts and decision lookup APIs | fail-closed executor behavior when token is missing/invalid |" in track
    assert "Governance enforcement stays in backend services, never in UI representation code." in track


def test_issue67_round5_superseded_markers_and_diary_closure_are_recorded() -> None:
    track = _load("docs/MCP_POLICY_EXECUTION_TRACK.md")
    diary = _load("docs/diary.md").lower()

    assert "## Superseded or Consolidated Issue Markers" in track
    assert "| #12 | closed predecessor | superseded by #45 and #46 policy/approval split |" in track
    assert "| #13 | closed predecessor | superseded by #48 for receipt integrity and ordering guardrails |" in track
    assert "Canonical successor track owner: #67." in track
    assert "Parent link update required in #62." in track
    assert "issue #67" in diary
    assert "mcp + policy execution track" in diary
    assert "dependency-ordered" in diary
    assert "superseded" in diary
