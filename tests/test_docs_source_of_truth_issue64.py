from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_round1_readme_quickstart_uses_real_runtime_commands() -> None:
    readme = _load("README.md")

    assert "PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001" in readme
    assert "npm --prefix apps/web start" in readme
    assert "./.venv/bin/pytest -q" in readme
    assert "pnpm install" not in readme
    assert "pnpm dev" not in readme


def test_round2_architecture_frontend_section_uses_actual_paths() -> None:
    architecture = _load("docs/ARCHITECTURE.md")

    assert "apps/web/view/index.html" in architecture
    assert "apps/web/view/app.js" in architecture
    assert "apps/web/model/timeline_model.js" in architecture
    assert "apps/web/controller/timeline_controller.js" in architecture


def test_round3_api_contract_uses_canonical_path_parameter_notation() -> None:
    api_md = _load("spec/API.md")

    assert "## GET /v1/runs/{run_id}/events" in api_md
    assert "## GET /v1/runs/{run_id}/status" in api_md
    assert "## POST /v1/approvals/{event_id}" in api_md
    assert "/v1/runs/:runId/events" not in api_md
    assert "/v1/runs/:runId/status" not in api_md
    assert "/v1/approvals/:eventId" not in api_md


def test_round4_business_rules_use_schema_field_names_and_runtime_semantics() -> None:
    rules = _load("spec/BUSINESS_RULES.md")

    assert "`id`" in rules
    assert "`type`" in rules
    assert "`meta.workflow`" in rules
    assert "`event_id`" not in rules
    assert "`event_type`" not in rules
    assert "`workflow_id`" not in rules
    assert "IF confidence > 1" not in rules
    assert "IF confidence < 0" not in rules
    assert "INVALID_CONFIDENCE_BOUNDS" in rules


def test_round5_readme_defines_canonical_contract_sources() -> None:
    readme = _load("README.md")

    assert "## Canonical Sources of Truth" in readme
    assert "docs/ARCHITECTURE.md" in readme
    assert "spec/API.md" in readme
    assert "spec/EVENT_SCHEMA.md" in readme
    assert "spec/BUSINESS_RULES.md" in readme
