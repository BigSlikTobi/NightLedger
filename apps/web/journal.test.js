import test from "node:test";
import assert from "node:assert/strict";
import { renderTimeline } from "./journal.js";

test("renders loading fallback for bad payload", () => {
  const html = renderTimeline(null);
  assert.match(html, /Could not read timeline data/);
});

test("renders empty state", () => {
  const html = renderTimeline([]);
  assert.match(html, /No journal events/);
});

test("renders timeline cards with risk + approval + evidence", () => {
  const html = renderTimeline([
    {
      title: "Spend request",
      summary: "Agent wants to buy API credits",
      timestamp: "2026-02-15T10:00:00.000Z",
      risk_level: "high",
      approval_status: "required",
      evidence_links: ["https://example.com/proof"],
    },
  ]);

  assert.match(html, /Spend request/);
  assert.match(html, /card--risk/);
  assert.match(html, /card--approval/);
  assert.match(html, /https:\/\/example.com\/proof/);
});
