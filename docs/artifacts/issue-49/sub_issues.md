# Issue #49 Sub-Issue Breakdown

Date: 2026-02-18

## Scope

Deliver a deterministic, reproducible purchase enforcement demo path for:
`block -> approve -> execute`, while preserving the existing Issue #54
`triage_inbox` demo workflow.

## Atomic Sub-Issues

### Sub-issue A — Docs-first contract lock for purchase demo acceptance

- Scope: add contract-lock tests that define required #49 docs and references.
- Acceptance:
  - tests fail before docs exist and pass after docs are added.
  - README references the purchase demo command path.

### Sub-issue B — One-command deterministic smoke script

- Scope: add one-command deterministic smoke script for
  `block -> approve -> execute`.
- Acceptance:
  - script proves `500 EUR` policy pause (`requires_approval`).
  - executor call without token is blocked.
  - approval + token mint + executor call succeeds.
  - output is operator-readable and deterministic.

### Sub-issue C — README and demo docs integration

- Scope: wire script into root docs for fresh-clone reproducibility.
- Acceptance:
  - README includes purchase demo section.
  - `docs/DEMO_SCRIPT.md` includes purchase path and evidence checklist.
  - existing Issue #54 triage flow remains intact.

### Sub-issue D — Committed verification artifact

- Scope: store a human-readable verification artifact for purchase flow.
- Acceptance:
  - committed artifact includes concrete request/response proof points.
  - artifact includes regenerate command.

### Sub-issue E — Post-implementation gap assessment and closure notes

- Scope: assess what #49 closes and what remains open in #62.
- Acceptance:
  - `docs/artifacts/issue-49/gap_assessment.md` maps remaining open gaps.
  - `docs/diary.md` records what was built, validation, and key findings.
