# 🗺️ Product Roadmap (Hackathon Edition)

> **Context:** This roadmap is optimized for a high-intensity Hackathon
> timeline. **North Star:** Deliver a "Wow" demo that proves Autonomy and
> Governance can coexist.

## 🟢 The Hackathon MVP

**Goal:** Prove the "Trust Loop": _Agent Acts → System Pauses → Human Approves →
Agent Resumes._ **Theme:** "Visualizing the Invisible."

### 1. The "Walking Skeleton" (Backend)

- [ ] **Event Ingestion API:** Simple generic endpoint (`POST /events`) to
      accept JSON payloads.
  - _Must handle:_ `run_id`, `event_type`, `timestamp`.
  - _Performance:_ Accept `risk_category` and `confidence_score` (0-1) fields.
- [ ] **Core Logic Engine:**
  - Implement the "Risk Rule": IF `requires_approval=true` THEN `status=PAUSED`.
  - **Risk Labeling:** Decorate events with clear risk labels based on input.
- [ ] **Journal Projection:** Logic to transform raw JSON events into
      human-readable one-liners (e.g., "Agent clicked 'Buy'").
- [ ] **Control API:** Endpoints to `GET /runs/{id}/status` and
      `POST /runs/{id}/approve`.
- [ ] **Storage:** In-memory or simple database (SQLite) for speed.

### 2. The "Control Tower" (Frontend)

- [ ] **Live Timeline UI:** The hero feature. Needs to be animated and slick.
  - Shows events appearing in real-time (polling or simulated).
  - **Journal View:** Displays the human-readable "story" alongside raw data.
- [ ] **The "Stop" Visual:** Dramatic visual state change when the agent hits a
      risk and pauses.
- [ ] **Approval Interaction:** A clear, satisfying "Authorize" button that
      resumes the flow.
- [ ] **Risk Heatmap (MVP Version):** Simple grid or color-coded blocks showing
      risk density (Scope: _Delighter Included_).

### 3. The Demo Narrative (Integration)

- [ ] **Simulation Script:** A script that acts as the "Agent".
  - It generates a series of mundane events (Low Risk).
  - It hits a predefined "High Risk" event (e.g., "Transfer $1M").
  - It waits for the API to say "RESUME" before finishing.
