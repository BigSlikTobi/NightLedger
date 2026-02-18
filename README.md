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
{"decision_id":"dec_...","state":"allow","reason_code":"POLICY_ALLOW_WITHIN_THRESHOLD"}
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
