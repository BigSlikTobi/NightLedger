export function createTimelineController({
  runId,
  getDemoEvents,
  getJournalEvents,
  onState,
}) {
  const state = {
    runId,
    status: "idle",
    error: "",
    events: [],
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

  return { state, load };
}
