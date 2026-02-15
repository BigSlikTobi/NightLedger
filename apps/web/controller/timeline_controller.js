export function createTimelineController({
  runId,
  getDemoEvents,
  getJournalEvents,
  listPendingApprovals,
  resolveApproval,
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
      state.pendingApprovals = await listPendingApprovals();
      state.pendingStatus = "success";
      emit();
    } catch (err) {
      state.pendingStatus = "error";
      state.pendingError = err?.message ?? "Unknown error";
      emit();
    }
  }

  async function submitApprovalDecision(eventId, decision) {
    if (state.pendingSubmissionByEventId[eventId]) return;

    state.pendingSubmissionByEventId[eventId] = true;
    emit();

    try {
      await resolveApproval(eventId, decision);
      state.pendingApprovals = state.pendingApprovals.filter((item) => item.event_id !== eventId);
      emit();
    } finally {
      state.pendingSubmissionByEventId[eventId] = false;
      emit();
    }
  }

  return { state, load, loadPendingApprovals, submitApprovalDecision };
}
