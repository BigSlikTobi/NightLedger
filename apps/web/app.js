import { renderTimeline } from "./journal.js";

function runIdFromLocation() {
  const url = new URL(window.location.href);
  return url.searchParams.get("runId") || "demo-run";
}

async function load() {
  const root = document.querySelector("#app");
  const runId = runIdFromLocation();

  root.innerHTML = `<div class="state">Loading timeline for <code>${runId}</code>...</div>`;

  try {
    const res = await fetch(`/v1/runs/${encodeURIComponent(runId)}/journal`);
    if (!res.ok) {
      throw new Error(`Request failed (${res.status})`);
    }

    const body = await res.json();
    const events = body.events ?? body.journal ?? [];

    root.innerHTML = `
      <header>
        <h1>Run Timeline</h1>
        <p class="muted">Run: <code>${runId}</code></p>
      </header>
      ${renderTimeline(events)}
    `;
  } catch (error) {
    root.innerHTML = `
      <header>
        <h1>Run Timeline</h1>
        <p class="muted">Run: <code>${runId}</code></p>
      </header>
      <div class="state state--error">Could not load journal timeline. ${error.message}</div>
    `;
  }
}

load();
