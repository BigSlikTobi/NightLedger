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
    onState: (state) => snapshots.push({ ...state }),
  });

  await controller.load();

  assert.equal(snapshots[0].status, "loading");
  assert.equal(snapshots.at(-1).status, "error");
  assert.match(snapshots.at(-1).error, /500/);
});
