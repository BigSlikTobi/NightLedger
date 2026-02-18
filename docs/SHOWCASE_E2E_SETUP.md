# End-to-End Showcase Setup (Non-Technical Playbook)

This guide is for running the real NightLedger showcase from start to finish:

1. Start NightLedger API
2. Start NightLedger UI
3. Start MCP server
4. Connect your bot to MCP
5. Trigger a real `500 EUR` purchase request
6. Approve in UI
7. Let bot continue and execute

No simulation script is required.

## What you need

- A Mac/Linux terminal
- This repo checked out locally
- Python virtual environment ready (`.venv`)
- Your bot runtime (OpenClaw or any MCP-capable bot)

Repo path used in examples:

`/Users/tobiaslatta/Projects/github/bigsliktobi/NightLedger`

---

## Step 0: Open 3 terminals

- Terminal A: API
- Terminal B: UI
- Terminal C: MCP server

In all terminals:

```bash
cd /Users/tobiaslatta/Projects/github/bigsliktobi/NightLedger
```

---

## Step 1: Start NightLedger API (Terminal A)

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

Leave this terminal running.

Success check:

- Open [http://127.0.0.1:8001/openapi.json](http://127.0.0.1:8001/openapi.json)
- You should see JSON in the browser.

---

## Step 2: Start NightLedger UI (Terminal B)

```bash
npm --prefix apps/web start
```

Leave this terminal running.

Open this URL in your browser:

`http://localhost:3000/view/?mode=live&runId=run_showcase_001&apiBase=http://127.0.0.1:8001`

Keep this tab open. You will approve there later.

---

## Step 3: Start MCP server (Terminal C)

Use one of these options.

### Option A (same machine bot): MCP stdio

```bash
PYTHONPATH=src ./.venv/bin/python -m nightledger_api.mcp_server
```

Use this when your bot connects to a local command-based MCP server.

### Option B (network bot): MCP remote HTTP

```bash
NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN=replace-with-strong-token \
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.mcp_remote_server:app --host 0.0.0.0 --port 8002
```

Use this when your bot connects over HTTP.

---

## Step 4: Add MCP server to your bot

Your bot must expose and use the `authorize_action` tool from NightLedger.

### If your bot uses stdio MCP

Set MCP command to:

`PYTHONPATH=src ./.venv/bin/python -m nightledger_api.mcp_server`

Working directory:

`/Users/tobiaslatta/Projects/github/bigsliktobi/NightLedger`

### If your bot uses remote MCP

- URL: `http://127.0.0.1:8002/v1/mcp/remote`
- Auth header: `Authorization: Bearer replace-with-strong-token`
- MCP protocol version: `2025-06-18`

---

## Step 5: Trigger the real risky request from the bot

Ask the bot to run a purchase request above threshold.

Use these exact values:

- `action`: `purchase.create`
- `amount`: `500`
- `currency`: `EUR`
- `merchant`: `ACME GmbH`
- `run_id`: `run_showcase_001`
- `request_id`: `req_showcase_001`

Expected bot behavior:

- Bot calls MCP `authorize_action`
- Receives `state=requires_approval`
- Stops/pause execution (fail-closed)

---

## Step 6: Ensure pending approval is registered

In v1 contract, bot must explicitly call:

`POST /v1/approvals/requests`

If your bot already does this, continue to Step 7.

If not, register manually once (copy-paste fallback):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/requests \
  -H "Content-Type: application/json" \
  -d '{"decision_id":"<DECISION_ID_FROM_BOT>","run_id":"run_showcase_001","requested_by":"openclaw","title":"Purchase approval required","details":"500 EUR exceeds threshold","risk_level":"high","reason":"Above threshold"}'
```

---

## Step 7: Approve in UI

Go to the UI page you opened:

`http://localhost:3000/view/?mode=live&runId=run_showcase_001&apiBase=http://127.0.0.1:8001`

In **Pending Approvals**:

1. Find the approval card
2. Click **Approve**

Expected:

- Pending card disappears
- Journal timeline updates

---

## Step 8: Bot resumes and completes

Bot should poll:

`GET /v1/approvals/decisions/{decision_id}`

When status becomes `approved`, bot should:

1. Mint token: `POST /v1/approvals/decisions/{decision_id}/execution-token`
2. Execute: `POST /v1/executors/purchase.create`

Expected final bot outcome:

- Execution succeeds
- Bot reports completion with execution receipt

---

## Step 9: Verify showcase receipts (optional but recommended)

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_showcase_001/status
curl -sS http://127.0.0.1:8001/v1/runs/run_showcase_001/journal
```

Look for:

- decision receipt (`authorize_action`)
- approval requested/resolved receipts
- execution token minted receipt
- `purchase.create executed` receipt

---

## Quick troubleshooting

- UI shows no pending approval:
  - Bot may have skipped `POST /v1/approvals/requests`
  - Use the manual fallback in Step 6

- Bot never resumes:
  - Check bot is polling `GET /v1/approvals/decisions/{decision_id}`
  - Confirm decision is `approved` in API response

- API errors:
  - Confirm API is running on `http://127.0.0.1:8001`
  - Confirm currency is `EUR`
  - Confirm amount is numeric

- MCP not visible in bot:
  - Re-check MCP command/URL config
  - Re-check auth token (remote mode)
