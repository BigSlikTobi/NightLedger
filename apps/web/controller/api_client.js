function _buildApiUrl(path, apiBase) {
  if (!apiBase) return path;
  return `${apiBase}${path}`;
}

async function _parseJsonOrEmpty(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export function createApiClient({ apiBase = "", fetcher = fetch } = {}) {
  async function _request(path, options = undefined) {
    const response = await fetcher(_buildApiUrl(path, apiBase), options);
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return _parseJsonOrEmpty(response);
  }

  return {
    async getJournalEvents(runId) {
      const body = await _request(`/v1/runs/${encodeURIComponent(runId)}/journal`);
      return body.events ?? body.journal ?? body.entries ?? [];
    },

    async listPendingApprovals() {
      const body = await _request("/v1/approvals/pending");
      return body.items ?? body.approvals ?? body.pending ?? [];
    },

    async resolveApproval(targetId, decision, context = {}) {
      const approverId = context.approverId || "human_approver";
      const reason = context.reason;
      const decisionId = context.decisionId;
      const eventId = context.eventId || targetId;
      const path = decisionId
        ? `/v1/approvals/decisions/${encodeURIComponent(decisionId)}`
        : `/v1/approvals/${encodeURIComponent(eventId)}`;

      return _request(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ decision, approver_id: approverId, reason }),
      });
    },
  };
}
