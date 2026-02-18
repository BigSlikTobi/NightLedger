import test from "node:test";
import assert from "node:assert/strict";
import { createTimelineController } from "./timeline_controller.js";

test("passes approver context to approval resolver", async () => {
  let captured = null;
  const controller = createTimelineController({
    runId: "run-ctx",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-ctx", title: "Approval" }],
    resolveApproval: async (targetId, decision, context) => {
      captured = { targetId, decision, context };
      return { ok: true };
    },
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("evt-ctx", "approved", { approverId: "human_approver", reason: "validated" });

  assert.deepEqual(captured, {
    targetId: "evt-ctx",
    decision: "approved",
    context: {
      approverId: "human_approver",
      reason: "validated",
      decisionId: undefined,
      eventId: "evt-ctx",
    },
  });
});

test("prefers decision_id when resolving pending approvals", async () => {
  let captured = null;
  const controller = createTimelineController({
    runId: "run-decision",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-ctx", decision_id: "dec-ctx", title: "Approval" }],
    resolveApproval: async (targetId, decision, context) => {
      captured = { targetId, decision, context };
      return { ok: true };
    },
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("dec-ctx", "approved", { approverId: "human_approver" });

  assert.deepEqual(captured, {
    targetId: "dec-ctx",
    decision: "approved",
    context: {
      approverId: "human_approver",
      decisionId: "dec-ctx",
      eventId: "evt-ctx",
    },
  });
});

test("loads demo events when runId is demo", async () => {
  const snapshots = [];
  const controller = createTimelineController({
    runId: "demo",
    getDemoEvents: async () => [{ title: "Demo" }],
    getJournalEvents: async () => {
      throw new Error("should not call API for demo");
    },
    listPendingApprovals: async () => [],
    resolveApproval: async () => ({ ok: true }),
    onState: (state) => snapshots.push({ ...state }),
  });

  await controller.load();

  assert.equal(snapshots[0].status, "loading");
  assert.equal(snapshots.at(-1).status, "success");
  assert.deepEqual(snapshots.at(-1).events, [{ title: "Demo" }]);
});

test("sets error state when journal API fails", async () => {
  const snapshots = [];
  const controller = createTimelineController({
    runId: "run-1",
    getDemoEvents: async () => [],
    getJournalEvents: async () => {
      throw new Error("Request failed (500)");
    },
    listPendingApprovals: async () => [],
    resolveApproval: async () => ({ ok: true }),
    onState: (state) => snapshots.push({ ...state }),
  });

  await controller.load();

  assert.equal(snapshots[0].status, "loading");
  assert.equal(snapshots.at(-1).status, "error");
  assert.match(snapshots.at(-1).error, /500/);
});

test("loads pending approvals", async () => {
  const controller = createTimelineController({
    runId: "run-1",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-1", title: "Spend Request" }],
    resolveApproval: async () => ({ ok: true }),
    onState: () => {},
  });

  await controller.loadPendingApprovals();

  assert.equal(controller.state.pendingStatus, "success");
  assert.equal(controller.state.pendingApprovals.length, 1);
  assert.equal(controller.state.pendingApprovals[0].event_id, "evt-1");
});

test("prevents duplicate approval submissions", async () => {
  let calls = 0;
  const controller = createTimelineController({
    runId: "demo",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-1", title: "Spend Request" }],
    resolveApproval: async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 5));
      return { ok: true };
    },
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await Promise.all([
    controller.submitApprovalDecision("evt-1", "approved", { approverId: "human_approver" }),
    controller.submitApprovalDecision("evt-1", "approved", { approverId: "human_approver" }),
  ]);

  assert.equal(calls, 1);
  assert.equal(controller.state.pendingApprovals.length, 0);
});

test("handles stale approval decision safely", async () => {
  const controller = createTimelineController({
    runId: "run-1",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [],
    resolveApproval: async () => ({ ok: true }),
    onState: () => {},
  });

  await controller.submitApprovalDecision("evt-missing", "approved", { approverId: "human_approver" });

  assert.equal(controller.state.pendingError, "Approval is no longer pending.");
});

test("keeps approval card visible when resolve fails and allows retry", async () => {
  let shouldFail = true;
  const controller = createTimelineController({
    runId: "demo",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-1", title: "Spend Request" }],
    resolveApproval: async () => {
      if (shouldFail) throw new Error("Request failed (500)");
      return { ok: true };
    },
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("evt-1", "approved", { approverId: "human_approver" });

  assert.equal(controller.state.pendingApprovals.length, 1);
  assert.match(controller.state.pendingError, /500/);

  shouldFail = false;
  await controller.submitApprovalDecision("evt-1", "approved", { approverId: "human_approver" });

  assert.equal(controller.state.pendingApprovals.length, 0);
  assert.equal(controller.state.pendingError, "");
});

test("refreshes live timeline and pending approvals after successful approval", async () => {
  let journalCalls = 0;
  let pendingCalls = 0;

  const controller = createTimelineController({
    runId: "run-live",
    getDemoEvents: async () => [],
    getJournalEvents: async () => {
      journalCalls += 1;
      return journalCalls === 1 ? [{ title: "before" }] : [{ title: "after" }];
    },
    listPendingApprovals: async () => {
      pendingCalls += 1;
      return pendingCalls === 1 ? [{ event_id: "evt-1", title: "Approval" }] : [];
    },
    resolveApproval: async () => ({ ok: true }),
    onState: () => {},
  });

  await controller.load();
  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("evt-1", "approved", { approverId: "human_approver" });

  assert.equal(journalCalls, 2);
  assert.equal(pendingCalls, 2);
  assert.equal(controller.state.events[0].title, "after");
  assert.equal(controller.state.pendingApprovals.length, 0);
});

test("emits decision logs for approval lifecycle", async () => {
  const logs = [];
  const controller = createTimelineController({
    runId: "run-live",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-42", title: "Approval" }],
    resolveApproval: async () => ({ ok: true }),
    logDecision: (entry) => logs.push(entry),
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("evt-42", "rejected", { approverId: "human_reviewer" });

  assert.deepEqual(logs, [
    {
      event: "approval_decision_requested",
      runId: "run-live",
      eventId: "evt-42",
      decision: "rejected",
      approverId: "human_reviewer",
    },
    {
      event: "approval_decision_completed",
      runId: "run-live",
      eventId: "evt-42",
      decision: "rejected",
      approverId: "human_reviewer",
    },
  ]);
});

test("emits failure decision log when approval request fails", async () => {
  const logs = [];
  const controller = createTimelineController({
    runId: "run-live",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [{ event_id: "evt-500", title: "Approval" }],
    resolveApproval: async () => {
      throw new Error("Request failed (500)");
    },
    logDecision: (entry) => logs.push(entry),
    onState: () => {},
  });

  await controller.loadPendingApprovals();
  await controller.submitApprovalDecision("evt-500", "approved", { approverId: "human_reviewer" });

  assert.deepEqual(logs, [
    {
      event: "approval_decision_requested",
      runId: "run-live",
      eventId: "evt-500",
      decision: "approved",
      approverId: "human_reviewer",
    },
    {
      event: "approval_decision_failed",
      runId: "run-live",
      eventId: "evt-500",
      decision: "approved",
      approverId: "human_reviewer",
      error: "Request failed (500)",
    },
  ]);
});

test("filters live pending approvals to current runId", async () => {
  const controller = createTimelineController({
    runId: "run-live-target",
    getDemoEvents: async () => [],
    getJournalEvents: async () => [],
    listPendingApprovals: async () => [
      { event_id: "evt-1", run_id: "run-live-target", title: "Target approval" },
      { event_id: "evt-2", run_id: "run-other", title: "Other run approval" },
      { event_id: "evt-3", title: "Legacy approval without run_id" },
    ],
    resolveApproval: async () => ({ ok: true }),
    onState: () => {},
  });

  await controller.loadPendingApprovals();

  assert.equal(controller.state.pendingApprovals.length, 2);
  assert.deepEqual(
    controller.state.pendingApprovals.map((item) => item.event_id),
    ["evt-1", "evt-3"]
  );
});
