# <img src="docs/images/nightledger_logo.png" width="80" alt="NightLedger 3D Logo" /> NightLedger: Autonomy with Receipts.

NightLedger is a lightweight runtime accountability layer for AI agents.
It captures append-only receipts, enforces risk gates, and makes approvals
explicit before high-risk actions execute.

## Vision, Mission, and MVP (at a glance)

- **Vision:** *The world runs on autonomous systems — safe, transparent, and accountable by default.*
- **Mission:** *Build the accountability infrastructure for the autonomous era.*
- **MVP:** prove one deterministic control loop from event capture to approval-gated resume.

## 60-second proof

**What happened**
- A run emits structured runtime events via `POST /v1/events`; operators view
  them as a human-readable timeline via `GET /v1/runs/{run_id}/journal`.

**What got blocked**
- A risky action transitions to `requires_approval`; execution pauses fail-closed
  until a human decision is recorded.

**Why this is trustworthy**
- Decisions and transitions are append-only, replayable, and exportable as
  tamper-evident receipts.

## Why NightLedger (vs plain logs / generic tracing)

| Concern | Plain logs / generic tracing | NightLedger |
| --- | --- | --- |
| Risk decisions | Usually descriptive only | Enforced runtime gate (`allow / requires_approval / deny`) |
| Human-in-the-loop | Often out-of-band | First-class approval lifecycle + explicit resume path |
| Auditability | Hard to prove order/integrity | Append-only event stream + audit export |
| Operator UX | Raw technical records | Journal/timeline projection for non-authors |
| Bot integration | Ad-hoc behavior | Deterministic API + MCP contract boundaries |

## Deconstructing Vision and MVP for Readers

### Vision

NightLedger is an accountability layer for the agentic era: autonomy with receipts.

### MVP

The MVP proves one full control loop:

1. Start run
2. Capture events
3. Hit a risk gate
4. Pause for approval
5. Approve/reject
6. Resume/stop with receipts

## Proof metrics (current)

- **Policy boundary is deterministic:** amount `<= 100 EUR` => `allow`, amount
  `> 100 EUR` => `requires_approval` (documented and contract-tested).
- **Approval loop is explicit:** unresolved decisions fail execution-token mint
  with `409 EXECUTION_DECISION_NOT_APPROVED`; mint succeeds only after approval.
- **One-command reproducibility:** deterministic `block -> approve -> execute`
  smoke flow available via `tasks/smoke_purchase_enforcement_demo.sh` (**Issue #49**).

## Quick start

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

## Local runtime

1. Start API (Terminal A):

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

2. Start web UI (Terminal B):

```bash
npm --prefix apps/web start
```

Open:

```text
http://localhost:3000/view/?mode=live&runId=run_triage_inbox_demo_1&apiBase=http://127.0.0.1:8001
```

## Deterministic purchase enforcement demo (Issue #49)

Run the `block -> approve -> execute` proof path:

```bash
bash tasks/smoke_purchase_enforcement_demo.sh
```

## Canonical Sources of Truth

| Concern | Canonical source |
| --- | --- |
| Runtime behavior and layer boundaries | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| HTTP API contract and error envelopes | [`spec/API.md`](spec/API.md) |
| Event payload schema contract | [`spec/EVENT_SCHEMA.md`](spec/EVENT_SCHEMA.md) |
| Governance/risk/approval rule catalog | [`spec/BUSINESS_RULES.md`](spec/BUSINESS_RULES.md) |

## Documentation map

| Doc | Purpose |
| --- | --- |
| [`README.md`](README.md) | Product overview + runnable proof path |
| [`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md) | Full conceptual + technical deep dive |
| [`spec/MVP/discovery.md`](spec/MVP/discovery.md) | Strategy and problem framing |
| [`spec/MVP/MVP.md`](spec/MVP/MVP.md) | MVP scope and success criteria |
| [`spec/MVP/product_design.md`](spec/MVP/product_design.md) | Layered design principles |
| [`spec/MVP/roadmap.md`](spec/MVP/roadmap.md) | Current execution roadmap |
| [`docs/API_TESTING.md`](docs/API_TESTING.md) | Local API smoke flows |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Reproducible demo handoff path |
| [`docs/SHOWCASE_E2E_SETUP.md`](docs/SHOWCASE_E2E_SETUP.md) | End-to-end showcase operator playbook |
| [`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md) | Branch/artifact hygiene policy |

## Hackathon Narrative (Last 5 Days)

This project originated in a 5-day hackathon built with OpenClaw + `Deborahbot`.
The build process and issue-sliced execution history are preserved in:

- [`agents.md`](agents.md)
- [`docs/diary.md`](docs/diary.md)
- [All issues](https://github.com/BigSlikTobi/NightLedger/issues)

## Technical deep dive

For implementation details, see:

- [`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md)
