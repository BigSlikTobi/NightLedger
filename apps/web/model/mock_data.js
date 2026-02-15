export const MOCK_EVENTS = [
  {
    title: "Session Started",
    summary: "New audit session initialized for researcher access.",
    timestamp: "2026-02-15T10:00:00.000Z",
    risk_level: "low",
    approval_status: "none"
  },
  {
    title: "Spend Request",
    summary: "Agent requested 50.00 USD for GPU compute credits.",
    timestamp: "2026-02-15T10:15:00.000Z",
    risk_level: "high",
    approval_status: "required",
    evidence_links: ["https://example.com/billing/quote-123", "https://example.com/compute/usage"]
  },
  {
    title: "Domain Access",
    summary: "Agent requested access to internal database 'vector-prod-01'.",
    timestamp: "2026-02-15T10:30:00.000Z",
    risk_level: "medium",
    approval_status: "pending"
  },
  {
    title: "Policy Update",
    summary: "System policy 'SP-004' updated to restrict outbound API calls.",
    timestamp: "2026-02-15T10:45:00.000Z",
    risk_level: "low",
    approval_status: "approved"
  },
  {
    title: "Credential Rotation",
    summary: "Automatic rotation of SSH keys for worker nodes failed.",
    timestamp: "2026-02-15T11:00:00.000Z",
    risk_level: "critical",
    approval_status: "rejected",
    evidence_links: ["https://example.com/logs/rotation-error"]
  }
];

export const MOCK_PENDING_APPROVALS = [
  {
    event_id: "evt_101",
    title: "AWS Spend Request",
    summary: "Agent requested 50.00 USD for GPU compute credits.",
    risk_level: "high",
    details: "This request is for a new experiment in the 'vector-prod-01' domain."
  },
  {
    event_id: "evt_102",
    title: "Database Access",
    summary: "Agent requested write access to internal database.",
    risk_level: "medium",
    details: "The agent needs to persist results of the compute run."
  }
];
