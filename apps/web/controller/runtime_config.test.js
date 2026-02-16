import test from "node:test";
import assert from "node:assert/strict";
import { resolveRuntimeConfig } from "./runtime_config.js";

test("defaults to demo mode when no query parameters are provided", () => {
  const config = resolveRuntimeConfig("http://localhost:3000/view/");

  assert.equal(config.mode, "demo");
  assert.equal(config.runId, "demo");
  assert.equal(config.apiBase, "");
});

test("uses live mode with default api base when runId is non-demo", () => {
  const config = resolveRuntimeConfig("http://localhost:3000/view/?runId=run_triage_inbox_demo_1");

  assert.equal(config.mode, "live");
  assert.equal(config.runId, "run_triage_inbox_demo_1");
  assert.equal(config.apiBase, "http://127.0.0.1:8001");
});

test("uses canonical live run id when mode=live and runId is not provided", () => {
  const config = resolveRuntimeConfig("http://localhost:3000/view/?mode=live");

  assert.equal(config.mode, "live");
  assert.equal(config.runId, "run_triage_inbox_demo_1");
  assert.equal(config.apiBase, "http://127.0.0.1:8001");
});
