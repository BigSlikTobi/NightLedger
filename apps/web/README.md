# NightLedger Web Journal

This is the web view for the NightLedger journal timeline.

## Quick Start

To view the timeline locally, run:

```bash
npm start
```

Then open [http://localhost:3000](http://localhost:3000) (or the port shown in
your terminal).

## Note on Local Viewing

This application uses **JavaScript Modules** (`type="module"`), which means it
**cannot** be opened directly by double-clicking `index.html` (the `file://`
protocol). It must be served via a local web server.

## Demo Mode

By default, if no `runId` is provided in the URL, the app defaults to a **demo
mode** using mock data. You can specify a run ID via the query string:

- Demo: `http://localhost:3000/`
- Specific Run: `http://localhost:3000/?runId=your-run-id`

## Runtime Query Params

- `runId`: target run identifier. `runId=demo` uses mock mode.
- `mode`: optional explicit mode override (`demo` or `live`).
- `apiBase`: optional API base URL for live mode (for example
  `http://127.0.0.1:8001`).

Deterministic fallback:
- no query params -> `demo` mode
- non-demo `runId` with no explicit `apiBase` -> live API defaults to
  `http://127.0.0.1:8001`
- explicit `mode=live` with no `runId` -> `run_triage_inbox_demo_1`

## Live Mode (UI + API)

From repo root, run this in two terminals.

Terminal A (API):

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

Terminal B (web):

```bash
npm --prefix apps/web start
```

Open:

```text
http://localhost:3000/view/?mode=live&runId=run_triage_inbox_demo_1&apiBase=http://127.0.0.1:8001
```

Demo mode remains available:

```text
http://localhost:3000/view/?mode=demo
```

Browser observability:
- Open DevTools console to see approval lifecycle logs:
  - `approval_decision_requested`
  - `approval_decision_completed`
  - `approval_decision_failed`
- Log payloads include run ID, event ID, decision, and approver ID when provided.

## Journal Mapping (Live Mode)

The web timeline maps `GET /v1/runs/{run_id}/journal` `entries` directly into
cards.

Primary live fields:
- readability text: `title`, `details`
- event identity: `entry_id`, `event_id`, `event_type`, `timestamp`
- risk and actor context: `metadata.risk_level`, `metadata.actor`
- approval state: `approval_context.status`, `approval_indicator`
- evidence links: `evidence_refs[*].ref` (with label/kind when present)
- traceability reference: `payload_ref.path` shown in card metadata

Backward compatibility:
- demo fixtures using `summary`, `approval_status`, and `evidence_links` are
  still supported.

Local cross-origin notes:
- API allows CORS from local web origins:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
  - `http://localhost:4173`
  - `http://127.0.0.1:4173`
