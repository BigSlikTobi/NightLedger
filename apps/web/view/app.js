import { createApp, computed, reactive } from "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js";
import { MOCK_EVENTS } from "../model/mock_data.js";
import { toTimelineCards } from "../model/timeline_model.js";
import { createTimelineController } from "../controller/timeline_controller.js";

function runIdFromLocation() {
  const url = new URL(window.location.href);
  return url.searchParams.get("runId") || "demo";
}

function fetchJournalEvents(runId) {
  return fetch(`/v1/runs/${encodeURIComponent(runId)}/journal`).then(async (res) => {
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    const body = await res.json();
    return body.events ?? body.journal ?? [];
  });
}

createApp({
  setup() {
    const state = reactive({
      runId: runIdFromLocation(),
      status: "idle",
      error: "",
      events: [],
    });

    const cards = computed(() => toTimelineCards(state.events));
    const isDemo = computed(() => state.runId === "demo");

    const controller = createTimelineController({
      runId: state.runId,
      getDemoEvents: async () => {
        await new Promise((resolve) => setTimeout(resolve, 350));
        return MOCK_EVENTS;
      },
      getJournalEvents: fetchJournalEvents,
      onState: (next) => {
        state.status = next.status;
        state.error = next.error;
        state.events = next.events;
      },
    });

    controller.load();

    return { state, cards, isDemo };
  },
  template: `
    <main>
      <header>
        <h1>Run Timeline<span v-if="isDemo"> (Demo)</span></h1>
        <p class="muted">Run: <code>{{ state.runId }}</code></p>
      </header>

      <div v-if="state.status === 'loading'" class="state">Loading timeline for <code>{{ state.runId }}</code>...</div>

      <div v-else-if="state.status === 'error'" class="state state--error">
        Could not load journal timeline. {{ state.error }}
      </div>

      <div v-else-if="cards.length === 0" class="state">No journal events for this run yet.</div>

      <ol v-else class="timeline">
        <li
          v-for="card in cards"
          :key="card.id"
          class="card"
          :class="{
            'card--risk': card.flags.isRisky,
            'card--approval': card.flags.needsApproval,
            'card--approved': card.flags.isApproved,
            'card--rejected': card.flags.isRejected
          }"
        >
          <div class="card__head">
            <h3>{{ card.title }}</h3>
            <time :datetime="card.timestamp">{{ card.timeText }}</time>
          </div>

          <p>{{ card.summary }}</p>

          <div class="meta">
            <span class="pill">risk: {{ card.riskLabel }}</span>
            <span class="pill">approval: {{ card.approvalLabel }}</span>
          </div>

          <div class="evidence" v-if="card.evidenceLinks.length > 0">
            <a
              v-for="url in card.evidenceLinks"
              :key="url"
              :href="url"
              target="_blank"
              rel="noreferrer"
            >evidence</a>
          </div>
          <div class="evidence muted" v-else>no evidence links</div>
        </li>
      </ol>
    </main>
  `,
}).mount("#app");
