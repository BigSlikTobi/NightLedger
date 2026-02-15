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
