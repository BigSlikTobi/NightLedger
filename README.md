# <img src="docs/images/nightledger_logo.png" width="80" alt="NightLedger 3D Logo" /> NightLedger: Autonomy with Receipts.

## Hackathon Narrative (Last 5 Days)

This repository is the output of a 5-day hackathon built around one assumption:

> Autonomous systems can be useful in production only if they are accountable
> by default.

We tried to prove or disprove that assumption with code, not slides.

Our working hypothesis:

1. Every meaningful agent step must be captured as append-only evidence.
2. Risky side effects must pause for explicit human approval.
3. The system must expose deterministic contracts that bots can integrate.
4. The resulting execution trail must be auditable by non-authors.

Result at MVP scope: the hypothesis holds for the implemented workflows.

## How We Build (agents.md)

The team coded under `agents.md` constraints:

1. Docs first when behavior changes.
2. TDD first (failing tests before implementation).
3. Strict layer separation (Capture / Governance / Representation).
4. No silent failures.
5. Atomic issue breakdown and atomic commits.
6. 5-round TDD + audit discipline.
7. Mandatory diary updates for completed issue work.

## Issues and Context

Hackathon delivery was issue-sliced to keep scope testable and mergeable:

- `#44`, `#45`, `#46`, `#47`, `#48`, `#49`
- `#63`, `#64`, `#66`, `#67`, `#75`, `#76`
- parent closure track: `#62`

This list is the hackathon implementation track, not the full project history.

Complete closed-issue history:

- [NightLedger closed issues](https://github.com/BigSlikTobi/NightLedger/issues?q=is%3Aissue+is%3Aclosed)

## High-Level Outcome

What was built:

1. Append-only runtime evidence capture.
2. Governance gates for risky actions (`requires_approval`).
3. Human approval lifecycle with explicit decision state.
4. Token-gated executor boundary for protected side effects.
5. Tamper-evident audit export path.
6. Deterministic demo flow (`block -> approve -> execute`).
7. Local + remote MCP integration path.

Why it matters:

- Turns "trust us" into verifiable receipts.
- Makes human override explicit and enforceable.
- Keeps governance in backend policy, not UI heuristics.

## Deconstructing Vision and MVP for Readers

### Vision

NightLedger is the accountability layer for the agentic era: autonomy with
receipts.

### MVP

The MVP proves one control loop end to end:

1. Start run
2. Capture events
3. Hit risk gate
4. Pause for approval
5. Approve/reject
6. Resume/stop with a full receipt trail

Out of scope in this phase: broader post-MVP intent-catalog evolution
(`#84/#85/#86`).

## Step-by-Step: Test and Run the System

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

### Quick Start (Local Runtime)

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

Run the proof path for `block -> approve -> execute`:

```bash
bash tasks/smoke_purchase_enforcement_demo.sh
```

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
| `README.md` | Vision, MVP, hackathon context, and quick-start navigation |
| `docs/TECHNICAL_GUIDE.md` | Full technical and integration deep dive |
| `spec/MVP/discovery.md` | Strategy and problem framing |
| `spec/MVP/MVP.md` | MVP scope and success criteria |
| `spec/MVP/product_design.md` | Layered design principles |
| `spec/MVP/roadmap.md` | Current execution roadmap |
| `docs/API_TESTING.md` | Local API smoke flows |
| `docs/DEMO_SCRIPT.md` | Reproducible demo handoff path |
| `docs/SHOWCASE_E2E_SETUP.md` | Non-technical end-to-end showcase operator playbook |
| `docs/REPO_HYGIENE.md` | Branch/artifact hygiene policy and cleanup workflow |

## Technical Deep Dive

For conceptual + technical details (contracts, runtime flow, endpoints,
transport, and implementation boundaries), use:

- `/Users/tobiaslatta/Projects/github/bigsliktobi/NightLedger/docs/TECHNICAL_GUIDE.md`
