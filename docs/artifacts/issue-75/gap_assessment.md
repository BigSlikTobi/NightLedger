# Issue #75 Post-Implementation Gap Assessment

Date: 2026-02-18

## 1) What #75 closed

Issue #75 acceptance criteria are implemented:

- Added a remote MCP transport endpoint for off-machine clients:
  `POST /v1/mcp/remote`, plus session stream and termination endpoints:
  `GET /v1/mcp/remote` and `DELETE /v1/mcp/remote`.
- Remote entrypoint supports `initialize`, `tools/list`, and `tools/call`, and
  now issues `MCP-Session-Id` on initialize with session-bound protocol checks
  via `MCP-Protocol-Version`.
- Added a fail-closed remote auth boundary using
  `NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN`, with support for either
  `Authorization: Bearer <token>` or `X-API-Key: <token>`.
- Added origin allowlist enforcement via
  `NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS`.
- Added OAuth protected-resource metadata endpoint:
  `GET /.well-known/oauth-protected-resource`.
- Added structured unauthorized and misconfigured auth error responses,
  including `WWW-Authenticate` bearer challenge header.
- Kept one shared MCP tool implementation in
  `src/nightledger_api/mcp_protocol.py` so stdio and remote wrappers stay
  behavior-identical for `authorize_action`.
- Added parity verification test proving decision identity across:
  HTTP contract endpoint, stdio MCP, and remote MCP.

## 2) Residual gaps against open issues

### #76 (adoption bootstrap + contract versioning)

- #75 provides the transport primitive, but #76 still needs runnable adoption
  packaging for external agent runtimes and contract versioning policy.

### #49 (deterministic end-to-end enforcement proof)

- #75 enables off-machine policy calls, but #49 still needs the complete
  deterministic demo artifact path (`block -> approve -> execute`) as one
  handoff flow.

### #62 (cleanup parent)

- #75 closes a critical runtime transport gap, but broader cleanup-parent
  backlog items remain open and must still be reconciled at parent issue level.

## 3) Risk notes and follow-ups

- Remote auth currently uses one shared static token value; OAuth token
  verification/introspection is still deployment-layer work.
- Session state is currently in-process memory only; multi-instance deployments
  need sticky routing or shared session backing.
- TLS termination is expected at deployment boundary (reverse proxy/ingress),
  not in-process.

## 4) Validation commands and results

- `PYTHONPATH=src ./.venv/bin/pytest -q tests/test_mcp_shared_protocol.py`
- `PYTHONPATH=src ./.venv/bin/pytest -q tests/test_mcp_remote_server.py`
- `PYTHONPATH=src ./.venv/bin/pytest -q tests/test_issue75_remote_mcp_docs.py tests/test_issue75_remote_mcp_parity.py`
- `PYTHONPATH=src ./.venv/bin/pytest -q`
- Result: `295 passed`.
