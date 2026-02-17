import test from "node:test";
import assert from "node:assert/strict";
import { toTimelineCards } from "./timeline_model.js";

test("returns empty list for bad payload", () => {
  assert.deepEqual(toTimelineCards(null), []);
});

test("sorts cards by timestamp ascending", () => {
  const cards = toTimelineCards([
    { title: "B", timestamp: "2026-02-15T11:00:00.000Z" },
    { title: "A", timestamp: "2026-02-15T10:00:00.000Z" },
  ]);

  assert.equal(cards[0].title, "A");
  assert.equal(cards[1].title, "B");
});

test("maps risk, approval and evidence metadata", () => {
  const [card] = toTimelineCards([
    {
      title: "Spend request",
      summary: "Agent wants to buy API credits",
      timestamp: "2026-02-15T10:00:00.000Z",
      risk_level: "critical",
      approval_status: "required",
      evidence_links: ["https://example.com/proof"],
    },
  ]);

  assert.equal(card.riskLabel, "CRITICAL");
  assert.equal(card.approvalLabel, "REQUIRED");
  assert.equal(card.flags.isRisky, true);
  assert.equal(card.flags.needsApproval, true);
  assert.deepEqual(card.evidenceLinks, ["https://example.com/proof"]);
});

test("round1 maps canonical journal entry readability and nested status metadata", () => {
  const [card] = toTimelineCards([
    {
      entry_id: "jrnl_run_1_0001",
      event_id: "evt_1",
      event_type: "approval_requested",
      title: "Approval required before transfer",
      details: "Transfer exceeds policy threshold",
      timestamp: "2026-02-15T10:00:00.000Z",
      metadata: { risk_level: "high", actor: "agent" },
      approval_context: { status: "pending" },
    },
  ]);

  assert.equal(card.id, "jrnl_run_1_0001");
  assert.equal(card.title, "Approval required before transfer");
  assert.equal(card.summary, "Transfer exceeds policy threshold");
  assert.equal(card.riskLabel, "HIGH");
  assert.equal(card.approvalLabel, "PENDING");
  assert.equal(card.flags.needsApproval, true);
});

test("round2 maps canonical evidence_refs into link targets and labeled evidence items", () => {
  const [card] = toTimelineCards([
    {
      entry_id: "jrnl_run_1_0002",
      event_id: "evt_2",
      title: "Collected receipts",
      details: "Evidence references were attached",
      timestamp: "2026-02-15T10:02:00.000Z",
      evidence_refs: [
        { kind: "log", label: "Runtime log", ref: "log://run-1/evt-2" },
        { kind: "artifact", label: "Diff bundle", ref: "artifact://bundle-2" },
      ],
    },
  ]);

  assert.deepEqual(card.evidenceLinks, [
    "log://run-1/evt-2",
    "artifact://bundle-2",
  ]);
  assert.deepEqual(card.evidenceItems, [
    { kind: "log", label: "Runtime log", ref: "log://run-1/evt-2" },
    { kind: "artifact", label: "Diff bundle", ref: "artifact://bundle-2" },
  ]);
});

test("round3 derives approval label from approval_indicator when status is absent", () => {
  const cards = toTimelineCards([
    {
      entry_id: "jrnl_run_1_0003",
      event_id: "evt_3",
      title: "Approval required",
      details: "Awaiting decision",
      timestamp: "2026-02-15T10:03:00.000Z",
      approval_indicator: {
        is_approval_required: true,
        is_approval_resolved: false,
        decision: null,
      },
    },
    {
      entry_id: "jrnl_run_1_0004",
      event_id: "evt_4",
      title: "Approval resolved",
      details: "Human approved the action",
      timestamp: "2026-02-15T10:04:00.000Z",
      approval_indicator: {
        is_approval_required: true,
        is_approval_resolved: true,
        decision: "approved",
      },
    },
  ]);

  assert.equal(cards[0].approvalLabel, "REQUIRED");
  assert.equal(cards[0].flags.needsApproval, true);
  assert.equal(cards[1].approvalLabel, "APPROVED");
  assert.equal(cards[1].flags.isApproved, true);
});

test("round4 exposes canonical traceability and actor metadata on card model", () => {
  const [card] = toTimelineCards([
    {
      entry_id: "jrnl_run_1_0005",
      event_id: "evt_5",
      event_type: "decision",
      title: "Decision logged",
      details: "Agent selected execution path B",
      timestamp: "2026-02-15T10:05:00.000Z",
      payload_ref: { path: "/v1/runs/run_1/events#evt_5" },
      metadata: { actor: "agent", risk_level: "medium" },
    },
  ]);

  assert.equal(card.eventType, "decision");
  assert.equal(card.actor, "agent");
  assert.equal(card.payloadPath, "/v1/runs/run_1/events#evt_5");
});
