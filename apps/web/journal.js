function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "unknown time";
  return date.toLocaleString();
}

function normalizeEvidenceLinks(event) {
  const links = event?.evidence_links ?? event?.evidenceLinks ?? [];
  return Array.isArray(links) ? links.filter(Boolean) : [];
}

function cardClasses(event) {
  const classes = ["card"];
  const risk = String(event?.risk_level ?? event?.riskLevel ?? "low").toLowerCase();
  const approval = String(event?.approval_status ?? event?.approvalStatus ?? "none").toLowerCase();

  if (risk === "high" || risk === "critical") classes.push("card--risk");
  if (approval === "required" || approval === "pending") classes.push("card--approval");
  if (approval === "approved") classes.push("card--approved");
  if (approval === "rejected") classes.push("card--rejected");

  return classes.join(" ");
}

export function renderTimeline(events) {
  if (!Array.isArray(events)) {
    return '<div class="state state--error">Could not read timeline data.</div>';
  }

  if (events.length === 0) {
    return '<div class="state">No journal events for this run yet.</div>';
  }

  const sorted = [...events].sort((a, b) => {
    const at = new Date(a?.timestamp ?? a?.at ?? 0).valueOf();
    const bt = new Date(b?.timestamp ?? b?.at ?? 0).valueOf();
    return at - bt;
  });

  return `<ol class="timeline">${sorted
    .map((event) => {
      const title = escapeHtml(event?.title ?? event?.kind ?? "Event");
      const summary = escapeHtml(event?.summary ?? event?.message ?? "No summary provided.");
      const timestamp = formatTime(event?.timestamp ?? event?.at);
      const risk = escapeHtml(String(event?.risk_level ?? event?.riskLevel ?? "low").toUpperCase());
      const approval = escapeHtml(String(event?.approval_status ?? event?.approvalStatus ?? "none").toUpperCase());
      const evidenceLinks = normalizeEvidenceLinks(event)
        .map((url) => `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">evidence</a>`)
        .join(" ");

      return `
        <li class="${cardClasses(event)}">
          <div class="card__head">
            <h3>${title}</h3>
            <time datetime="${escapeHtml(event?.timestamp ?? event?.at ?? "")}">${escapeHtml(timestamp)}</time>
          </div>
          <p>${summary}</p>
          <div class="meta">
            <span class="pill">risk: ${risk}</span>
            <span class="pill">approval: ${approval}</span>
          </div>
          <div class="evidence">${evidenceLinks || '<span class="muted">no evidence links</span>'}</div>
        </li>`;
    })
    .join("")}</ol>`;
}
