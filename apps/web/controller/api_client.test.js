import test from "node:test";
import assert from "node:assert/strict";
import { createApiClient } from "./api_client.js";

test("builds journal request against configured live api base", async () => {
  const calls = [];
  const fetcher = async (url) => {
    calls.push(url);
    return {
      ok: true,
      async json() {
        return { entries: [] };
      },
    };
  };
  const client = createApiClient({ apiBase: "http://127.0.0.1:8001", fetcher });

  await client.getJournalEvents("run_live");
  await client.listPendingApprovals();

  assert.deepEqual(calls, [
    "http://127.0.0.1:8001/v1/runs/run_live/journal",
    "http://127.0.0.1:8001/v1/approvals/pending",
  ]);
});

test("uses relative paths when api base is empty", async () => {
  const calls = [];
  const fetcher = async (url) => {
    calls.push(url);
    return {
      ok: true,
      async json() {
        return {};
      },
    };
  };
  const client = createApiClient({ apiBase: "", fetcher });

  await client.resolveApproval("evt_1", "approved", { approverId: "human", reason: "ok" });

  assert.equal(calls[0], "/v1/approvals/evt_1");
});
