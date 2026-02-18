export function createTimelineController({
  runId,
  getDemoEvents,
  getJournalEvents,
  listPendingApprovals,
  getDemoPendingApprovals,
  resolveApproval,
  logDecision = () => {},
  onState,
}) {
  const state = {
    runId,
    status: "idle",
    error: "",
    events: [],
    pendingStatus: "idle",
    pendingError: "",
    pendingApprovals: [],
    pendingSubmissionByEventId: {},
  };

  function emit() {
    onState?.(state);
  }

  async function load() {
    state.status = "loading";
    state.error = "";
    emit();

    try {
      state.events = runId === "demo" ? await getDemoEvents() : await getJournalEvents(runId);
      state.status = "success";
      emit();
    } catch (err) {
      state.status = "error";
      state.error = err?.message ?? "Unknown error";
      emit();
    }
  }

  async function loadPendingApprovals() {
    state.pendingStatus = "loading";
    state.pendingError = "";
    emit();

    try {
      const approvals = runId === "demo" && getDemoPendingApprovals
        ? await getDemoPendingApprovals()
        : await listPendingApprovals();
      state.pendingApprovals = _filterApprovalsForRun(approvals, runId);
      state.pendingStatus = "success";
      emit();
    } catch (err) {
      state.pendingStatus = "error";
      state.pendingError = err?.message ?? "Unknown error";
      emit();
    }
  }

  function _filterApprovalsForRun(approvals, currentRunId) {
    if (!Array.isArray(approvals)) return [];
    if (currentRunId === "demo") return approvals;
    return approvals.filter((item) => {
      if (!item || typeof item !== "object") return false;
      if (!("run_id" in item)) return true;
      const run = item.run_id;
      if (typeof run !== "string") return true;
      return run.trim() === "" || run === currentRunId;
    });
  }

  async function submitApprovalDecision(eventId, decision, context = {}) {
    const pendingItem = state.pendingApprovals.find((item) => {
      const itemRef = item.decision_id || item.event_id;
      return itemRef === eventId || item.event_id === eventId;
    });
    if (!pendingItem) {
      state.pendingError = "Approval is no longer pending.";
      emit();
      return;
    }
    const submissionId = pendingItem.decision_id || pendingItem.event_id;

    if (state.pendingSubmissionByEventId[submissionId]) return;

    state.pendingSubmissionByEventId[submissionId] = true;
    state.pendingError = "";
    emit();
    const approverId = context?.approverId;
    const decisionId = pendingItem.decision_id;
    const logIdentity = decisionId ? { eventId: pendingItem.event_id, decisionId } : { eventId: pendingItem.event_id };
    logDecision({
      event: "approval_decision_requested",
      runId,
      ...logIdentity,
      decision,
      approverId,
    });

    try {
      await resolveApproval(submissionId, decision, {
        ...context,
        decisionId,
        eventId: pendingItem.event_id,
      });
      logDecision({
        event: "approval_decision_completed",
        runId,
        ...logIdentity,
        decision,
        approverId,
      });
      if (runId === "demo") {
        state.pendingApprovals = state.pendingApprovals.filter((item) => {
          const itemRef = item.decision_id || item.event_id;
          return itemRef !== submissionId;
        });
        emit();
      } else {
        await load();
        await loadPendingApprovals();
      }
    } catch (err) {
      logDecision({
        event: "approval_decision_failed",
        runId,
        ...logIdentity,
        decision,
        approverId,
        error: err?.message ?? "Unknown error",
      });
      state.pendingError = err?.message ?? "Could not resolve approval.";
      emit();
    } finally {
      state.pendingSubmissionByEventId[submissionId] = false;
      emit();
    }
  }

  return { state, load, loadPendingApprovals, submitApprovalDecision };
}
