# NightLedger Technical Guide

This document is the technical deep dive for NightLedger.

Vision/MVP/hackathon narrative lives in `/README.md`.

## Quick Navigation

- Runtime/API contracts: `spec/API.md`
- Event schema: `spec/EVENT_SCHEMA.md`
- Rule catalog: `spec/BUSINESS_RULES.md`
- Architecture boundaries: `docs/ARCHITECTURE.md`

## Architecture and Code Walkthrough

### 1) Capture Layer

Primary concern: ingest immutable runtime events.

- Endpoints and controllers in `src/nightledger_api/controllers/`.
- Event model/schema validation in `src/nightledger_api/models/event_schema.py`.
- Append-only stores in `src/nightledger_api/services/event_store.py`.

### 2) Governance Layer

Primary concern: policy and enforcement decisions.

- Policy and authorization in `src/nightledger_api/services/authorize_action_service.py` and `src/nightledger_api/services/business_rules_service.py`.
- Approval lifecycle in `src/nightledger_api/services/approval_service.py`.
- Execution-token issuance and trust checks in `src/nightledger_api/services/execution_token_service.py`.

### 3) Representation Layer

Primary concern: project immutable data into human-readable state.

- Run status projection in `src/nightledger_api/services/run_status_service.py`.
- Journal projection in `src/nightledger_api/services/journal_projection_service.py`.
- UI model/controller/view in `apps/web/model`, `apps/web/controller`, and `apps/web/view`.

### Runtime and Transport Entry Points

- API runtime app: `src/nightledger_api/main.py`
- MCP stdio: `src/nightledger_api/mcp_server.py`
- MCP remote HTTP transport: `src/nightledger_api/mcp_remote_server.py`
- Shared MCP protocol core: `src/nightledger_api/mcp_protocol.py`

## Step-by-Step: Integrate and Implement Against NightLedger

Implementation flow for real bot runtimes:

1. Call `authorize_action` over MCP or HTTP.
2. If decision is `allow`, proceed.
3. If decision is `requires_approval`, pause fail-closed.
4. Register pending approval and surface it to human operator UI.
5. Poll decision endpoint until approved/rejected.
6. If approved, mint execution token.
7. Execute protected side effect with token.
8. Export audit receipts when needed.

## Real bot workflow (Issue #49 v1)

This is the production-facing contract for a real bot integration using
`MCP + HTTP`:

1. Bot calls MCP `authorize_action`.
2. If decision is `allow`, bot proceeds.
3. If decision is `requires_approval`, bot pauses fail-closed.
4. Bot explicitly registers pending approval:
   `POST /v1/approvals/requests`.
5. User approves/rejects in UI (`/view/?mode=live&runId=<run_id>&apiBase=...`).
6. Bot polls `GET /v1/approvals/decisions/{decision_id}`.
7. If approved, bot mints token:
   `POST /v1/approvals/decisions/{decision_id}/execution-token`.
8. Bot executes with token:
   `POST /v1/executors/purchase.create`.

No simulation is required for this flow. OpenClaw (or any independent bot)
should implement these contract steps directly.

## MCP authorize_action (Issue #44 v1 contract)

Endpoint:

```text
POST /v1/mcp/authorize_action
```

Policy rule (Issue #45 sub-issue 1):

- `context.amount` and `context.currency` are required policy inputs.
- Default threshold: `100` EUR (override with
  `NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR`).
- `amount <= threshold` => `allow`
- `amount > threshold` => `requires_approval`
- `transport_decision_hint` (`allow|requires_approval|deny`) is accepted for
  backward compatibility but does not override policy outcome.

Allow response (`amount` at threshold):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_allow","amount":100,"currency":"EUR","transport_decision_hint":"deny"}}'
```

```json
{"decision_id":"dec_...","state":"allow","reason_code":"POLICY_ALLOW_WITHIN_THRESHOLD","execution_token":"<signed-token>","execution_token_expires_at":"2026-02-18T12:05:00Z"}
```

Requires approval response (`amount` above threshold):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_pause","amount":101,"currency":"EUR","transport_decision_hint":"allow"}}'
```

```json
{"decision_id":"dec_...","state":"requires_approval","reason_code":"AMOUNT_ABOVE_THRESHOLD"}
```

Invalid payload example (`intent.action` not supported):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"transfer.create"},"context":{"request_id":"req_invalid","amount":50,"currency":"EUR"}}'
```

```json
{"error":{"code":"REQUEST_VALIDATION_ERROR","details":[{"path":"intent.action","code":"UNSUPPORTED_ACTION"}]}}
```

### MCP stdio server wrapper

Run the MCP wrapper on stdio:

```bash
PYTHONPATH=src ./.venv/bin/python -m nightledger_api.mcp_server
```

The wrapper exposes one MCP tool, `authorize_action`, backed by the same
deterministic contract used by `POST /v1/mcp/authorize_action`.

### MCP remote server wrapper

Use this when your MCP client is on a different machine than NightLedger.

server machine:

```bash
NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN=replace-with-strong-token \
NIGHTLEDGER_MCP_REMOTE_ALLOWED_ORIGINS=https://trusted-client.example \
NIGHTLEDGER_MCP_REMOTE_AUTHORIZATION_SERVERS=https://auth.example \
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.mcp_remote_server:app --host 0.0.0.0 --port 8002
```

client machine:

```bash
curl -sS -X POST http://<server-ip>:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer replace-with-strong-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"remote-client","version":"0.1.0"}}}'
```

Initialization response includes `MCP-Session-Id`. Reuse it for all subsequent
transport calls together with `MCP-Protocol-Version: 2025-06-18`.

Validate tool exposure:

```bash
curl -sS -X POST http://<server-ip>:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer replace-with-strong-token" \
  -H "MCP-Session-Id: <session-id-from-initialize>" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Validate remote policy decision:

```bash
curl -sS -X POST http://<server-ip>:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer replace-with-strong-token" \
  -H "MCP-Session-Id: <session-id-from-initialize>" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"authorize_action","arguments":{"intent":{"action":"purchase.create"},"context":{"request_id":"req_remote_1","amount":101,"currency":"EUR"}}}}'
```

Open server-sent event stream for async notifications:

```bash
curl -N -sS http://<server-ip>:8002/v1/mcp/remote \
  -H "Accept: text/event-stream" \
  -H "Authorization: Bearer replace-with-strong-token" \
  -H "MCP-Session-Id: <session-id-from-initialize>" \
  -H "MCP-Protocol-Version: 2025-06-18"
```

Close the remote MCP session:

```bash
curl -sS -X DELETE http://<server-ip>:8002/v1/mcp/remote \
  -H "Authorization: Bearer replace-with-strong-token" \
  -H "MCP-Session-Id: <session-id-from-initialize>" \
  -H "MCP-Protocol-Version: 2025-06-18"
```

Inspect OAuth protected-resource metadata:

```bash
curl -sS http://<server-ip>:8002/.well-known/oauth-protected-resource
```

Token auth options:

- `Authorization: Bearer <token>`
- `X-API-Key: <token>`

### Bot MCP config examples

Use these as templates for agent runtimes that support HTTP MCP servers.

Claude Desktop (local stdio):

```json
{
  "mcpServers": {
    "nightledger-local": {
      "command": "/Users/<your-user>/Projects/github/bigsliktobi/NightLedger/.venv/bin/python",
      "args": [
        "-m",
        "nightledger_api.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/Users/<your-user>/Projects/github/bigsliktobi/NightLedger/src"
      }
    }
  }
}
```

OpenHands/Cline-style (remote HTTP MCP):

```json
{
  "name": "nightledger-remote",
  "url": "http://<server-ip>:8002/v1/mcp/remote",
  "headers": {
    "Authorization": "Bearer <token>",
    "Accept": "application/json",
    "MCP-Protocol-Version": "2025-06-18"
  }
}
```

Generic remote MCP server config:

```json
{
  "name": "nightledger-remote",
  "transport": {
    "type": "http",
    "url": "http://<server-ip>:8002/v1/mcp/remote",
    "headers": {
      "Authorization": "Bearer <token>",
      "Accept": "application/json"
    }
  },
  "protocolVersion": "2025-06-18"
}
```

If your client supports explicit session header persistence between calls, keep:

```json
{
  "sessionHeaders": {
    "MCP-Session-Id": "<value-returned-by-initialize>",
    "MCP-Protocol-Version": "2025-06-18"
  }
}
```

For clients that support SSE stream subscriptions, configure:

```json
{
  "stream": {
    "method": "GET",
    "url": "http://<server-ip>:8002/v1/mcp/remote",
    "headers": {
      "Authorization": "Bearer <token>",
      "Accept": "text/event-stream",
      "MCP-Session-Id": "<session-id>",
      "MCP-Protocol-Version": "2025-06-18"
    }
  }
}
```

OAuth metadata discovery endpoint (if your bot platform supports it):

```text
http://<server-ip>:8002/.well-known/oauth-protected-resource
```

## Adoption v1 Quickstart (Issue #76)

One command boots API + MCP runtime for local adoption flows:

```bash
bash tasks/bootstrap_nightledger_runtime.sh
```

This path is designed to prove setup -> connect -> call tool in under 10 minutes,
including both API + MCP process startup.

## Adoption v1 demo flow (under 10 minutes)

1) Start both services:

```bash
bash tasks/bootstrap_nightledger_runtime.sh
```

2) Initialize MCP session:

```bash
curl -sS -X POST http://127.0.0.1:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer nightledger-local-dev-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"adoption-demo","version":"0.1.0"}}}'
```

3) List tools:

```bash
curl -sS -X POST http://127.0.0.1:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer nightledger-local-dev-token" \
  -H "MCP-Session-Id: <session-id>" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

4) Call authorize_action:

```bash
curl -sS -X POST http://127.0.0.1:8002/v1/mcp/remote \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer nightledger-local-dev-token" \
  -H "MCP-Session-Id: <session-id>" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"authorize_action","arguments":{"intent":{"action":"purchase.create"},"context":{"request_id":"req_demo_76","amount":101,"currency":"EUR"}}}}'
```

## Policy Threshold Operator Flow (Issue #45)

Use terminal requests for policy evaluation and keep UI focused on approval
state projection.

1) Start API with threshold `100`:

```bash
NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR=100 \
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --port 8001
```

2) Send policy decision requests:

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_120","amount":120,"currency":"EUR"}}'
```

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_80","amount":80,"currency":"EUR"}}'
```

3) Inspect pending approvals (UI reads from this endpoint):

```bash
curl -sS http://127.0.0.1:8001/v1/approvals/pending
```

Notes:
- `authorize_action` returns decisions; it does not append timeline receipts by
  itself.
- To visualize custom scenarios in live UI/journal, append matching
  `approval_requested` or `action` events via `POST /v1/events`.

## Decision-ID Approval Flow (Issue #46)

New approval lifecycle endpoints:

- `POST /v1/approvals/requests` to register pending approval by `decision_id`
- `POST /v1/approvals/decisions/{decision_id}` to approve/reject once
- `GET /v1/approvals/decisions/{decision_id}` to query approval result

Legacy compatibility:

- `POST /v1/approvals/{event_id}` remains available during migration.

## Token-Gated Executor Flow (Issue #47)

NightLedger enforces a hard runtime trust boundary for `purchase.create`.

1. Policy decision:
   `POST /v1/mcp/authorize_action` returns `allow` or `requires_approval`.
   Include `context.run_id` to bind generated runtime receipts to a specific
   live timeline run.
2. Approval token minting:
   `POST /v1/approvals/decisions/{decision_id}/execution-token` returns a short-lived
   `execution_token` only when the decision is approved and binds token to the
   requested purchase payload (`amount`, `currency`, `merchant`).
3. Protected execution:
   `POST /v1/executors/purchase.create` requires
   `Authorization: Bearer <execution_token>`.

Fail-closed behavior:

- Missing token -> blocked.
- Invalid/tampered token -> blocked.
- Expired token -> blocked.
- Replayed token -> blocked.

Token mint and execution examples:

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/decisions/dec_123/execution-token \
  -H "Content-Type: application/json" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}'
```

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/executors/purchase.create \
  -H "Authorization: Bearer <signed-token>" \
  -H "Content-Type: application/json" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}'
```

Security runtime config:

- `NIGHTLEDGER_EXECUTION_TOKEN_SECRET`: signing secret (legacy single-key mode)
- `NIGHTLEDGER_EXECUTION_TOKEN_KEYS`: comma-separated `kid:secret` keyring
- `NIGHTLEDGER_EXECUTION_TOKEN_ACTIVE_KID`: active key identifier for minting
- `NIGHTLEDGER_EXECUTION_TOKEN_REPLAY_DB_PATH`: durable replay store path

Runtime receipt persistence config:

- `NIGHTLEDGER_EVENT_STORE_BACKEND`: `memory` (default) or `sqlite`
- `NIGHTLEDGER_EVENT_STORE_DB_PATH`: sqlite file path when backend is `sqlite`

When `context.run_id` is set, authorize/mint/execute flows append runtime
receipt events that are visible in:

- `GET /v1/runs/{run_id}/events`
- `GET /v1/runs/{run_id}/journal`

## Audit Export Flow (Issue #48)

NightLedger now exposes tamper-evident decision audit exports:

- `GET /v1/approvals/decisions/{decision_id}/audit-export`

Export payload includes deterministic integrity chain fields for every exported
receipt:

- `prev_hash`
- `hash`

Example:

```bash
curl -sS http://127.0.0.1:8001/v1/approvals/decisions/dec_123/audit-export
```
