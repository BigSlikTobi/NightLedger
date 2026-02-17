function toDateValue(raw) {
  const value = new Date(raw).valueOf();
  return Number.isNaN(value) ? 0 : value;
}

function normalizeEvidenceItems(event) {
  const canonical = event?.evidence_refs;
  if (Array.isArray(canonical)) {
    return canonical
      .filter((item) => item && item.ref)
      .map((item) => ({
        kind: String(item.kind ?? "evidence"),
        label: String(item.label ?? "evidence"),
        ref: String(item.ref),
      }));
  }

  const legacy = event?.evidence_links ?? event?.evidenceLinks ?? [];
  if (!Array.isArray(legacy)) return [];
  return legacy.filter(Boolean).map((ref) => ({
    kind: "evidence",
    label: "evidence",
    ref: String(ref),
  }));
}

function normalizeEvidenceLinks(event) {
  return normalizeEvidenceItems(event).map((item) => item.ref);
}

function normalizeSummary(event) {
  return event?.summary ?? event?.details ?? event?.message ?? "No summary provided.";
}

function normalizeRiskValue(event) {
  return event?.risk_level ?? event?.riskLevel ?? event?.metadata?.risk_level;
}

function normalizeApprovalValue(event) {
  const value = event?.approval_status ?? event?.approvalStatus ?? event?.approval_context?.status;
  if (value === "not_required") return "none";
  if (value) return value;

  const indicator = event?.approval_indicator;
  if (indicator?.is_approval_resolved) {
    return indicator?.decision ?? "approved";
  }
  if (indicator?.is_approval_required) {
    return "required";
  }
  return undefined;
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
      const riskLabel = normalizeLabel(normalizeRiskValue(event), "low");
      const approvalLabel = normalizeLabel(normalizeApprovalValue(event), "none");

      return {
        id: event?.entry_id ?? event?.event_id ?? event?.id ?? `${event?.title ?? event?.kind ?? "event"}-${event?.timestamp ?? event?.at ?? ""}`,
        eventId: event?.event_id ?? event?.id ?? "",
        eventType: event?.event_type ?? event?.type ?? event?.kind ?? "",
        actor: event?.metadata?.actor ?? event?.actor ?? "",
        payloadPath: event?.payload_ref?.path ?? "",
        title: event?.title ?? event?.kind ?? "Event",
        summary: normalizeSummary(event),
        timestamp: event?.timestamp ?? event?.at ?? "",
        timeText: formatTime(event?.timestamp ?? event?.at),
        riskLabel,
        approvalLabel,
        evidenceLinks: normalizeEvidenceLinks(event),
        evidenceItems: normalizeEvidenceItems(event),
        flags: {
          isRisky: riskLabel === "HIGH" || riskLabel === "CRITICAL",
          needsApproval: approvalLabel === "REQUIRED" || approvalLabel === "PENDING",
          isApproved: approvalLabel === "APPROVED",
          isRejected: approvalLabel === "REJECTED",
        },
      };
    });
}
