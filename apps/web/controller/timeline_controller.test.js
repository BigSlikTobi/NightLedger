import test from "node:test";
import assert from "node:assert/strict";
import { createTimelineController } from "./timeline_controller.js";

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
    runId: "run-1",
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
    controller.submitApprovalDecision("evt-1", "approved"),
    controller.submitApprovalDecision("evt-1", "approved"),
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

  await controller.submitApprovalDecision("evt-missing", "approved");

  assert.equal(controller.state.pendingError, "Approval is no longer pending.");
});

test("keeps approval card visible when resolve fails and allows retry", async () => {
  let shouldFail = true;
  const controller = createTimelineController({
    runId: "run-1",
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
  await controller.submitApprovalDecision("evt-1", "approved");

  assert.equal(controller.state.pendingApprovals.length, 1);
  assert.match(controller.state.pendingError, /500/);

  shouldFail = false;
  await controller.submitApprovalDecision("evt-1", "approved");

  assert.equal(controller.state.pendingApprovals.length, 0);
  assert.equal(controller.state.pendingError, "");
});
