# Issue #49 OpenClaw Real Workflow

Date: 2026-02-18

This document defines the real bot contract for OpenClaw using NightLedger
`MCP decision + HTTP approval lifecycle`.

No simulation is used in this workflow.

## Step-by-step contract

Step 1: Bot calls MCP decision tool (`authorize_action`) for `purchase.create`.

Step 2: NightLedger evaluates hardcoded rule (`amount > 100 EUR`).

Step 3: If decision is `allow`, bot may continue.

Step 4: If decision is `requires_approval`, bot must pause fail-closed.

Step 5: Bot explicitly creates approval request:
`POST /v1/approvals/requests`.

Step 6: Server exposes pending approval in UI (`/view/?mode=live&runId=...`).

Step 7: Human approval is resolved in UI (`approved` or `rejected`).

Step 8: Bot polls `GET /v1/approvals/decisions/{decision_id}` and only resumes
on `approved`; on `rejected` it aborts.

## MCP decision + HTTP lifecycle mapping

- MCP decision: `authorize_action`
- HTTP lifecycle: register -> poll -> mint token -> execute
- Human approval remains mandatory for `requires_approval` decisions.

## Operator notes

- Polling defaults for bot implementation:
  - interval: 2s
  - timeout: 300s
- Keep bot fail-closed on timeout or non-approved terminal state.
