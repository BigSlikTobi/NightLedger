import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appSource = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");

test("round5 template renders canonical journal metadata fields", () => {
  assert.match(appSource, /card\.eventType/);
  assert.match(appSource, /card\.actor/);
  assert.match(appSource, /card\.payloadPath/);
  assert.match(appSource, /card\.evidenceItems/);
});

test("round5 live mode polling refresh is wired", () => {
  assert.match(appSource, /setInterval\(\(\) => \{/);
  assert.match(appSource, /controller\.load\(\)/);
  assert.match(appSource, /controller\.loadPendingApprovals\(\)/);
  assert.match(appSource, /clearInterval/);
});
