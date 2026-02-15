import { createApp, computed, ref } from "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js";
import { MOCK_EVENTS } from "./mock_data.js";
import { toTimelineCards } from "./timeline_model.js";

function runIdFromLocation() {
  const url = new URL(window.location.href);
  return url.searchParams.get("runId") || "demo";
}

createApp({
  setup() {
    const runId = ref(runIdFromLocation());
    const status = ref("loading");
    const error = ref("");
    const events = ref([]);

    const cards = computed(() => toTimelineCards(events.value));
    const isDemo = computed(() => runId.value === "demo");

    async function loadJournal() {
      status.value = "loading";
      error.value = "";

      if (isDemo.value) {
        await new Promise((resolve) => setTimeout(resolve, 350));
        events.value = MOCK_EVENTS;
        status.value = "success";
        return;
      }

      try {
        const res = await fetch(`/v1/runs/${encodeURIComponent(runId.value)}/journal`);
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const body = await res.json();
        events.value = body.events ?? body.journal ?? [];
        status.value = "success";
      } catch (err) {
        status.value = "error";
        error.value = err?.message ?? "Unknown error";
      }
    }

    loadJournal();

    return { runId, status, error, cards, isDemo };
  },
  template: `
    <main>
      <header>
        <h1>Run Timeline<span v-if="isDemo"> (Demo)</span></h1>
        <p class="muted">Run: <code>{{ runId }}</code></p>
      </header>

      <div v-if="status === 'loading'" class="state">Loading timeline for <code>{{ runId }}</code>...</div>

      <div v-else-if="status === 'error'" class="state state--error">
        Could not load journal timeline. {{ error }}
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
