# Issue #76 Post-Implementation Gap Assessment

Date: 2026-02-18

## 1) What #76 closed

Issue #76 acceptance criteria are implemented:

- Added one-command runtime bootstrap path for local adoption:
  `bash tasks/bootstrap_nightledger_runtime.sh`.
- Added local and remote MCP client configuration templates in `README.md`
  including session header expectations for remote MCP.
- Added explicit `authorize_action` contract version marker in runtime and MCP
  tool metadata:
  - response field: `contract_version`
  - MCP tool metadata: `x-nightledger-contract.version`
- Documented compatibility and deprecation policy in `spec/API.md`.
- Added test locks for bootstrap command docs/script presence, client config
  snippets, and contract version marker behavior.
- Added an under-10-minute setup/connect/call demo sequence in `README.md`.

## 2) Residual gaps against open issues

### #49 (deterministic end-to-end enforcement proof)

- #76 improves setup and integration onboarding, but #49 still needs a complete
  deterministic proof artifact path for block -> approve -> execute output.

### #62 (cleanup parent)

- #76 closes adoption bootstrap and interface versioning gaps, but cleanup
  parent scope still requires broader consolidation and closure updates.

## 3) Risk notes and follow-ups

- Bootstrap currently starts two local uvicorn processes and is optimized for
  developer adoption, not production orchestration.
- Remote auth bootstrap still defaults to a local dev token if not overridden;
  production deployments must set strong secret values explicitly.
- Multi-instance deployment posture (shared session/state, externalized auth)
  remains operational hardening work.

## 4) Validation commands and results

- `PYTHONPATH=src ./.venv/bin/pytest -q tests/test_issue76_adoption_docs.py`
- `PYTHONPATH=src ./.venv/bin/pytest -q tests/test_issue76_contract_versioning.py`
- `PYTHONPATH=src ./.venv/bin/pytest -q`
- Result: `303 passed`.
