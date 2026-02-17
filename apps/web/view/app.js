import { createApp, computed, reactive } from "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js";
import { MOCK_EVENTS, MOCK_PENDING_APPROVALS } from "../model/mock_data.js";
import { toTimelineCards } from "../model/timeline_model.js";
import { createApiClient } from "../controller/api_client.js";
import { resolveRuntimeConfig } from "../controller/runtime_config.js";
import { createTimelineController } from "../controller/timeline_controller.js";

createApp({
  setup() {
    const runtime = resolveRuntimeConfig(
      window.location.href,
      window.__NIGHTLEDGER_API_BASE__ ?? ""
    );
    const apiClient = createApiClient({ apiBase: runtime.apiBase });

    const state = reactive({
      runId: runtime.runId,
      mode: runtime.mode,
      status: "idle",
      error: "",
      events: [],
      pendingStatus: "idle",
      pendingError: "",
      pendingApprovals: [],
      pendingSubmissionByEventId: {},
    });

    const cards = computed(() => toTimelineCards(state.events));
    const isDemo = computed(() => state.mode === "demo");

    const controller = createTimelineController({
      runId: state.runId,
      getDemoEvents: async () => {
        await new Promise((resolve) => setTimeout(resolve, 350));
        return MOCK_EVENTS;
      },
      getJournalEvents: apiClient.getJournalEvents,
      listPendingApprovals: apiClient.listPendingApprovals,
      getDemoPendingApprovals: async () => {
        await new Promise((resolve) => setTimeout(resolve, 250));
        return MOCK_PENDING_APPROVALS;
      },
      resolveApproval: apiClient.resolveApproval,
      logDecision: (entry) => {
        const tag = `[nightledger-ui] ${entry.event}`;
        if (entry.event === "approval_decision_failed") {
          console.warn(tag, entry);
          return;
        }
        console.info(tag, entry);
      },
      onState: (next) => {
        state.status = next.status;
        state.error = next.error;
        state.events = next.events;
        state.pendingStatus = next.pendingStatus;
        state.pendingError = next.pendingError;
        state.pendingApprovals = next.pendingApprovals;
        state.pendingSubmissionByEventId = next.pendingSubmissionByEventId;
      },
    });

    controller.load();
    controller.loadPendingApprovals();

    function onApprove(eventId) {
      return controller.submitApprovalDecision(eventId, "approved");
    }

    function onReject(eventId) {
      return controller.submitApprovalDecision(eventId, "rejected");
    }

    return { state, cards, isDemo, onApprove, onReject };
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

      <section class="pending">
        <h2>Pending Approvals</h2>
        <div v-if="state.pendingStatus === 'loading'" class="state">Loading pending approvals…</div>
        <div v-else-if="state.pendingStatus === 'error'" class="state state--error">
          Could not load pending approvals. {{ state.pendingError }}
        </div>
        <template v-else>
          <div v-if="state.pendingError" class="state state--error">{{ state.pendingError }}</div>
          <div v-if="state.pendingApprovals.length === 0" class="state">No pending approvals.</div>
          <div v-else class="pending-list">
            <article v-for="item in state.pendingApprovals" :key="item.event_id" class="card card--approval">
              <div class="card__head">
                <h3>{{ item.title || item.event_id }}</h3>
                <span class="pill">risk: {{ (item.risk_level || 'unknown').toUpperCase() }}</span>
              </div>
              <p>{{ item.summary || item.details || 'Approval required.' }}</p>
              <div class="actions">
                <button
                  @click="onApprove(item.event_id)"
                  :disabled="state.pendingSubmissionByEventId[item.event_id]"
                >Approve</button>
                <button
                  @click="onReject(item.event_id)"
                  :disabled="state.pendingSubmissionByEventId[item.event_id]"
                >Reject</button>
              </div>
            </article>
          </div>
        </template>
      </section>

      <div v-if="state.status === 'success' && cards.length === 0" class="state">No journal events for this run yet.</div>

      <ol v-if="state.status === 'success' && cards.length > 0" class="timeline">
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
            <span class="pill" v-if="card.eventType">type: {{ card.eventType.toUpperCase() }}</span>
            <span class="pill" v-if="card.actor">actor: {{ card.actor.toUpperCase() }}</span>
          </div>

          <div class="muted" v-if="card.eventId || card.payloadPath">
            <code v-if="card.eventId">event: {{ card.eventId }}</code>
            <code v-if="card.payloadPath"> trace: {{ card.payloadPath }}</code>
          </div>

          <div class="evidence" v-if="card.evidenceItems.length > 0">
            <a
              v-for="item in card.evidenceItems"
              :key="item.ref"
              :href="item.ref"
              target="_blank"
              rel="noreferrer"
            >{{ item.label }} ({{ item.kind }})</a>
          </div>
          <div class="evidence muted" v-else>no evidence links</div>
        </li>
      </ol>
    </main>
  `,
}).mount("#app");
