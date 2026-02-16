const DEFAULT_LIVE_API_BASE = "http://127.0.0.1:8001";
const DEFAULT_LIVE_RUN_ID = "run_triage_inbox_demo_1";
const VALID_MODES = new Set(["demo", "live"]);

function _normalizeApiBase(value) {
  if (!value || typeof value !== "string") return "";
  return value.trim().replace(/\/+$/, "");
}

export function resolveRuntimeConfig(locationHref, injectedApiBase = "") {
  const url = new URL(locationHref);
  const runId = (url.searchParams.get("runId") || "").trim() || "demo";
  const modeParam = (url.searchParams.get("mode") || "").trim().toLowerCase();
  const mode = VALID_MODES.has(modeParam) ? modeParam : runId === "demo" ? "demo" : "live";

  if (mode === "demo") {
    return { mode, runId: "demo", apiBase: "" };
  }

  const liveRunId = runId === "demo" ? DEFAULT_LIVE_RUN_ID : runId;
  const apiBaseFromQuery = _normalizeApiBase(url.searchParams.get("apiBase"));
  const apiBaseFromConfig = _normalizeApiBase(injectedApiBase);

  return {
    mode,
    runId: liveRunId,
    apiBase: apiBaseFromQuery || apiBaseFromConfig || DEFAULT_LIVE_API_BASE,
  };
}
