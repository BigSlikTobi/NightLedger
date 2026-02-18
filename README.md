# <img src="docs/images/nightledger_logo.png" width="80" alt="NightLedger 3D Logo" /> NightLedger: Autonomy with Receipts.

NightLedger is an accountability layer for agent workflows: append-only event
capture, governance gating for risky actions, and human-readable receipts.

## Canonical Sources of Truth

Use one primary document per concern to avoid contract drift:

| Concern | Canonical source |
| --- | --- |
| Runtime behavior and layer boundaries | `docs/ARCHITECTURE.md` |
| HTTP API contract and error envelopes | `spec/API.md` |
| Event payload schema contract | `spec/EVENT_SCHEMA.md` |
| Governance/risk/approval rule catalog | `spec/BUSINESS_RULES.md` |

## Documentation Map

| Doc | Purpose |
| --- | --- |
| `spec/MVP/discovery.md` | Strategy and problem framing |
| `spec/MVP/MVP.md` | MVP scope and success criteria |
| `spec/MVP/product_design.md` | Layered design principles |
| `spec/MVP/roadmap.md` | Current execution roadmap |
| `docs/API_TESTING.md` | Local API smoke flows |
| `docs/DEMO_SCRIPT.md` | Reproducible demo handoff path |
| `docs/REPO_HYGIENE.md` | Branch/artifact hygiene policy and cleanup workflow |

## Quick Start (Fresh Clone)

```bash
git clone https://github.com/bigsliktobi/NightLedger.git
cd NightLedger
python -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
```

## Local Verification (Matches CI)

```bash
./.venv/bin/pytest -q
cd apps/web
node --test model/*.test.js controller/*.test.js view/*.test.js
```

## Quick Start (Local Runtime)

### 1) Start API (Terminal A)

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

### 2) Start web UI (Terminal B)

```bash
npm --prefix apps/web start
```

Open:

```text
http://localhost:3000/view/?mode=live&runId=run_triage_inbox_demo_1&apiBase=http://127.0.0.1:8001
```

## Local Demo Data Reset

```bash
bash tasks/reset_seed_triage_inbox_demo.sh
```

This seeds a deterministic paused run (`run_triage_inbox_demo_1`) for approval
and journal demo flows.

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
