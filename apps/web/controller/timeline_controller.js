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
      state.pendingApprovals = runId === "demo" && getDemoPendingApprovals
        ? await getDemoPendingApprovals()
        : await listPendingApprovals();
      state.pendingStatus = "success";
      emit();
    } catch (err) {
      state.pendingStatus = "error";
      state.pendingError = err?.message ?? "Unknown error";
      emit();
    }
  }

  async function submitApprovalDecision(eventId, decision, context = {}) {
    const isKnownPending = state.pendingApprovals.some((item) => item.event_id === eventId);
    if (!isKnownPending) {
      state.pendingError = "Approval is no longer pending.";
      emit();
      return;
    }

    if (state.pendingSubmissionByEventId[eventId]) return;

    state.pendingSubmissionByEventId[eventId] = true;
    state.pendingError = "";
    emit();
    const approverId = context?.approverId;
    logDecision({
      event: "approval_decision_requested",
      runId,
      eventId,
      decision,
      approverId,
    });

    try {
      await resolveApproval(eventId, decision, context);
      logDecision({
        event: "approval_decision_completed",
        runId,
        eventId,
        decision,
        approverId,
      });
      if (runId === "demo") {
        state.pendingApprovals = state.pendingApprovals.filter((item) => item.event_id !== eventId);
        emit();
      } else {
        await load();
        await loadPendingApprovals();
      }
    } catch (err) {
      logDecision({
        event: "approval_decision_failed",
        runId,
        eventId,
        decision,
        approverId,
        error: err?.message ?? "Unknown error",
      });
      state.pendingError = err?.message ?? "Could not resolve approval.";
      emit();
    } finally {
      state.pendingSubmissionByEventId[eventId] = false;
      emit();
    }
  }

  return { state, load, loadPendingApprovals, submitApprovalDecision };
}
