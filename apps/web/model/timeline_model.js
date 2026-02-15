function toDateValue(raw) {
  const value = new Date(raw).valueOf();
  return Number.isNaN(value) ? 0 : value;
}

function normalizeEvidenceLinks(event) {
  const links = event?.evidence_links ?? event?.evidenceLinks ?? [];
  return Array.isArray(links) ? links.filter(Boolean) : [];
}

function normalizeLabel(value, fallback) {
  return String(value ?? fallback).toUpperCase();
}

export function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "unknown time";
  return date.toLocaleString();
}

export function toTimelineCards(events) {
  if (!Array.isArray(events)) return [];

  return [...events]
    .sort((a, b) => toDateValue(a?.timestamp ?? a?.at) - toDateValue(b?.timestamp ?? b?.at))
    .map((event) => {
      const riskLabel = normalizeLabel(event?.risk_level ?? event?.riskLevel, "low");
      const approvalLabel = normalizeLabel(event?.approval_status ?? event?.approvalStatus, "none");

      return {
        id: event?.id ?? `${event?.title ?? event?.kind ?? "event"}-${event?.timestamp ?? event?.at ?? ""}`,
        title: event?.title ?? event?.kind ?? "Event",
        summary: event?.summary ?? event?.message ?? "No summary provided.",
        timestamp: event?.timestamp ?? event?.at ?? "",
        timeText: formatTime(event?.timestamp ?? event?.at),
        riskLabel,
        approvalLabel,
        evidenceLinks: normalizeEvidenceLinks(event),
        flags: {
          isRisky: riskLabel === "HIGH" || riskLabel === "CRITICAL",
          needsApproval: approvalLabel === "REQUIRED" || approvalLabel === "PENDING",
          isApproved: approvalLabel === "APPROVED",
          isRejected: approvalLabel === "REJECTED",
        },
      };
    });
}
