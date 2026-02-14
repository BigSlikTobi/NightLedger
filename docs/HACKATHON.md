# NightLedger Hackathon — Clawbot-Created Build Sprint

## What this is

This is a **Clawbot-created hackathon** started by Tobi and Deborabotter (Clawbot) to build the first working version of **NightLedger**: an app that makes autonomous agent work visible, reviewable, and controllable by humans.

It starts as a focused 1:1 builder sprint (human + bot), with the explicit option to later evolve into a broader multi-bot hackathon format in molt-book.

## Motivation

AI agents can now execute real workflows, but trust and operations are lagging behind.
Teams still struggle to answer basic questions:
- What did the agent do?
- Why did it do that?
- What evidence supports this step?
- Where can a human intervene before risky actions happen?

NightLedger exists to close that trust gap.

## Why we are doing this now

The trigger was a clear pattern observed across recent industry signals:

1. **Agent workflows are moving into default delivery surfaces**
   - Evidence: GitHub launched technical preview capabilities for agentic workflows in Actions.
   - Implication: automation is becoming operational, not experimental.

2. **Operating model is shifting to continuous/background AI**
   - Evidence: market framing is moving from chat-only copilots toward persistent autonomous operations.
   - Implication: teams need always-on accountability, not one-off prompts.

3. **Adoption bottleneck is governance, not raw model quality**
   - Evidence: increasing emphasis on identity, policy, auditability, permissions, and runtime controls.
   - Implication: trust infrastructure is now the critical product layer.

4. **Safety and reliability need explicit guardrails in production**
   - Evidence: repeated discussion of safety drift and the need for evals/observability in CI and runtime.
   - Implication: actions must leave a readable audit trail and support human checkpoints.

These observations directly triggered the NightLedger concept: **autonomy with receipts**.

## Goal (Hackathon Outcome)

Ship a working Week-1 vertical slice where:

- an agent run emits structured events,
- events are transformed into human-readable journal entries,
- risky steps require explicit human approval,
- approval resumes execution,
- every decision links back to evidence.

In short: prove that agent operations can be both fast **and** trustworthy.

## Success criteria

By the end of this sprint, we can demo one complete run (`triage_inbox`) with:

- clear event timeline,
- approval gate in the loop,
- understandable narrative for non-engineers,
- evidence-backed traceability for operators.

## Ownership model

- **Tobi:** UI lane (timeline, approval UX)
- **Deborabotter (Clawbot):** runtime lane (event schema, ingestion, approval state machine, journal rendering)
- Shared integration checkpoints twice per day.

## North-star statement

NightLedger makes AI agents operationally trustworthy by default:
**every autonomous action is visible, explainable, and interruptible.**
