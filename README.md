# NightLedger

Autonomy with receipts.

NightLedger is a lightweight system that makes agent work auditable and trustworthy: every run becomes a clear human-readable journal entry with evidence, confidence, and explicit approval state.

## Week 1 Goal

Ship one real end-to-end workflow:
- an agent run emits structured events
- events are rendered as readable journal entries
- risky actions require human approval

## Repo Layout

- `spec/` product + technical specs
- `apps/web/` journal UI + approval UX
- `apps/api/` ingest + approval gate API
- `tasks/` hackathon board + ownership
- `docs/` architecture decisions + demo notes

## Quick Start

```bash
# 1) install deps (to be finalized by implementation)
# pnpm install

# 2) run services
# pnpm dev
```

## Principles

- Human-readable by default
- Structured events under the hood
- Safety gates for irreversible/risky actions
- Minimal ceremony, fast iteration
