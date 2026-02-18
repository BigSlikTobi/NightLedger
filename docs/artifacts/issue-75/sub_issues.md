# Issue #75 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues.

## Sub-issue A (contract + docs foundation)

- Scope: Define remote MCP transport contract, auth boundary, and operator setup docs.
- Done when:
  - `spec/API.md` includes remote MCP transport method and auth contract.
  - `README.md` includes server/client machine demo setup.
  - `docs/artifacts/issue-75/sub_issues.md` exists.

## Sub-issue B (shared MCP tool core)

- Scope: Centralize MCP tool definitions + method handling for stdio and remote wrappers.
- Done when:
  - Stdio and remote wrappers call one shared MCP handler.
  - `authorize_action` behavior stays deterministic and schema-identical.

## Sub-issue C (remote transport entrypoint)

- Scope: Add shippable remote streamable HTTP MCP server entrypoint.
- Done when:
  - Remote entrypoint supports `initialize`, `tools/list`, and `tools/call`.
  - JSON-RPC framing remains strict and deterministic.

## Sub-issue D (remote auth + failure paths)

- Scope: Enforce token-based auth (`Bearer` or API key) for remote MCP.
- Done when:
  - Unauthenticated requests fail closed with structured error responses.
  - Authenticated requests complete the MCP flow.

## Sub-issue E (closure + assessment)

- Scope: Final closure artifacts and backlog gap reconciliation.
- Done when:
  - `docs/artifacts/issue-75/gap_assessment.md` exists.
  - `docs/diary.md` contains #75 summary and validation evidence.
