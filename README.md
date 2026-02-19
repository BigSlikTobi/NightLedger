# <img src="docs/images/nightledger_logo.png" width="80" alt="NightLedger 3D Logo" /> NightLedger: Autonomy with Receipts.

## Hackathon Narrative (Last 5 Days)

This codebase is the result of my 5-day hackathon executed with my OpenClaw
agent, `Deborrabotter`.

### Technical Problem I Wanted to Solve

Current agent tooling is strong at execution but weak at accountability:

1. Autonomous actions can happen without immutable receipts.
2. High-risk steps are often gated by ad-hoc prompts instead of enforceable
   runtime policy.
3. Human approval is frequently disconnected from the exact decision context.
4. Integrations often lack deterministic contracts for pause/resume behavior.

This hackathon focused on solving that systems gap by building a runtime layer
that is append-only, policy-gated, approval-aware, and contract-driven.

The assumption tested was simple:

> If autonomous systems must show their work before real-world impact,
> autonomy can be deployed with trust instead of blind faith.

The goal was to prove or disprove that assumption through running software,
contract tests, and deterministic demos.

Key hypothesis checks:

1. Every meaningful step is captured as append-only evidence.
2. Risky side effects are paused for explicit human approval.
3. Bot integrations can rely on deterministic API/MCP contracts.
4. The execution trail is auditable by people outside the authoring loop.

Result at MVP scope: this hypothesis is supported by the implemented flows.

## How This Was Built (agents.md)

I followed the repo constitution in [`agents.md`](agents.md):

1. Docs-first for behavior changes.
2. TDD-first (failing tests before implementation).
3. Strict separation of concerns (Capture / Governance / Representation).
4. No silent failures.
5. Atomic issue breakdown and commits.
6. 5-round TDD + audit discipline.
7. Diary updates for every completed issue.

## Issues and Context

I executed the hackathon as issue-sliced delivery tracked in GitHub.

For complete history and current status:

- [All issues](https://github.com/BigSlikTobi/NightLedger/issues)
- [Open issues](https://github.com/BigSlikTobi/NightLedger/issues?q=is%3Aissue+is%3Aopen)
- [Closed issues](https://github.com/BigSlikTobi/NightLedger/issues?q=is%3Aissue+is%3Aclosed)

## High-Level Outcome

What I implemented:

1. Append-only runtime accountability.
2. Governance gates for risky actions.
3. Human approval lifecycle.
4. Token-gated protected execution.
5. Tamper-evident audit export.
6. Deterministic proof demo paths.
7. Local and remote MCP integration support.

## Deconstructing Vision and MVP for Readers

### Vision

NightLedger is an accountability layer for the agentic era: autonomy with
receipts.

Related source documents:

- [`spec/MVP/discovery.md`](spec/MVP/discovery.md)
- [`spec/MVP/MVP.md`](spec/MVP/MVP.md)
- [`spec/MVP/product_design.md`](spec/MVP/product_design.md)

### MVP

The MVP proves one full control loop:

1. Start run
2. Capture events
3. Hit a risk gate
4. Pause for approval
5. Approve/reject
6. Resume/stop with receipts

Post-MVP items remain tracked separately (for example `#84/#85/#86`).

Related implementation contracts:

- [`spec/API.md`](spec/API.md)
- [`spec/EVENT_SCHEMA.md`](spec/EVENT_SCHEMA.md)
- [`spec/BUSINESS_RULES.md`](spec/BUSINESS_RULES.md)
- [`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md)

## Step-by-Step: Test and Run

### Quick Start (Fresh Clone)

```bash
git clone https://github.com/bigsliktobi/NightLedger.git
cd NightLedger
python -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
```

### Local Verification (Matches CI)

```bash
./.venv/bin/pytest -q
cd apps/web
node --test model/*.test.js controller/*.test.js view/*.test.js
```

### Local Runtime

1) Start API (Terminal A):

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

2) Start web UI (Terminal B):

```bash
npm --prefix apps/web start
```

Open:

```text
http://localhost:3000/view/?mode=live&runId=run_triage_inbox_demo_1&apiBase=http://127.0.0.1:8001
```

### Deterministic purchase enforcement demo (Issue #49)

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

## Documentation Map

| Doc | Purpose |
| --- | --- |
| [`README.md`](README.md) | Vision, MVP, and hackathon context |
| [`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md) | Full conceptual + technical deep dive |
| [`spec/MVP/discovery.md`](spec/MVP/discovery.md) | Strategy and problem framing |
| [`spec/MVP/MVP.md`](spec/MVP/MVP.md) | MVP scope and success criteria |
| [`spec/MVP/product_design.md`](spec/MVP/product_design.md) | Layered design principles |
| [`spec/MVP/roadmap.md`](spec/MVP/roadmap.md) | Current execution roadmap |
| [`docs/API_TESTING.md`](docs/API_TESTING.md) | Local API smoke flows |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Reproducible demo handoff path |
| [`docs/SHOWCASE_E2E_SETUP.md`](docs/SHOWCASE_E2E_SETUP.md) | End-to-end showcase operator playbook |
| [`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md) | Branch/artifact hygiene policy |

## Technical Deep Dive

For the conceptual + technical implementation details, use:

- [`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md)
