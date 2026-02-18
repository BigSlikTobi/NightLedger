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

Allow response (default transport behavior):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_allow","transport_decision_hint":"allow"}}'
```

```json
{"decision_id":"dec_...","state":"allow","reason_code":"TRANSPORT_CONTRACT_ACCEPTED"}
```

Requires approval response:

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_pause","transport_decision_hint":"requires_approval"}}'
```

```json
{"decision_id":"dec_...","state":"requires_approval","reason_code":"TRANSPORT_REQUIRES_APPROVAL"}
```

Deny response:

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_deny","transport_decision_hint":"deny"}}'
```

```json
{"decision_id":"dec_...","state":"deny","reason_code":"TRANSPORT_DENIED"}
```

Invalid payload example (`intent.action` not supported):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/mcp/authorize_action \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"transfer.create"},"context":{"request_id":"req_invalid"}}'
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
