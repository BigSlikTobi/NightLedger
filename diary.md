# Diary

## 2026-02-15 — Issue #6 Journal Timeline Refactor (The Big Slik Way)

Today was intense, and honestly useful.

I started by syncing the branch with the latest remote updates and then took time to understand the current structure before touching anything. The biggest context changes were your demo-mode integration and the updated `agents.md` direction in `main`.

I followed the 5-step loop as requested, with practical iterations inside each step.

### Step 1 — Pattern investigation and scope lock

I reviewed the existing timeline implementation, your new demo-mode flow, and the repo conventions. I compared branch state against `origin/main`, checked what had been added, and inspected where the UI currently lived.

Finding: the timeline worked, but it was still plain DOM-string rendering, which would get harder to maintain once interactions and navigation grow.

Iteration: I decided to move to a framework-based structure while keeping demo mode and API mode behavior intact.

### Step 2 — Tests first (TDD entry point)

Before the refactor, I rewrote the tests to target a view-model transformation layer instead of HTML string rendering. This gives us stable tests that focus on behavior: ordering, risk/approval mapping, and evidence link normalization.

Finding: once tests targeted data-shaping instead of markup details, the refactor path became safer and cleaner.

Iteration: created failing tests that expected a new `toTimelineCards()` model function.

### Step 3 — Implementation (minimal code to satisfy tests)

I introduced a new `timeline_model.js` and implemented `toTimelineCards()` with deterministic sorting and normalized flags/labels. Then I refactored `app.js` to a Vue 3 app mounted from `index.html`.

Finding: separating model logic from rendering removed most complexity from the UI component and made state handling straightforward.

Iteration: preserved both runtime paths:
- `runId=demo` uses mock events for local viewing,
- non-demo run IDs call `/v1/runs/:runId/journal`.

### Step 4 — Verification loop

I ran the test suite in `apps/web` and confirmed all tests pass after refactor. I also re-checked status boundaries manually in code: loading, error, empty, and success rendering paths.

Finding: the Vue structure now gives us a clean base for future controls (filters, grouping, timeline navigation, interaction states) without rewriting architecture later.

Iteration: made small template and mount refinements so the root app container and rendering flow stay consistent.

### Step 5 — Final audit and hygiene

I aligned documentation and constitution expectations first, then cleaned accidental tracked artifacts (`__pycache__`, `.pyc`) and hardened `.gitignore` so this noise won’t reappear.

Findings from audit:
- Documentation needed to explicitly describe frontend representation layering.
- The branch had binary Python cache files that should not be versioned.
- Commit granularity needed to stay atomic and fast.

Iterations completed:
1. docs + constitution alignment,
2. test-first refactor prep,
3. framework migration,
4. artifact cleanup.

Overall progress: strong. The timeline is now in a modern framework, demo mode remains easy to use, tests validate core behavior, and the branch is cleaner and easier to evolve.

## 2026-02-15 — MVC follow-up and communication correction

After the first refactor, I received the explicit direction to move the frontend into an MVC style and to follow the updated `agents.md` from `main` with the full cycle discipline.

I had a communication gap during execution. That was a process failure on my side, and I corrected it by resuming with a complete cycle and immediate push.

### Full cycle completed (not just red tests)

1. Goal re-read
   I re-read the request: keep Vue, but split responsibilities in MVC form and preserve demo/runtime behavior.

2. Pattern investigation
   I inspected `app.js` and identified orchestration logic mixed into the view setup. This was the main separation gap.

3. Failing tests
   I added controller-level tests in `timeline_controller.test.js` for two core orchestration behaviors:
   - demo run loads local data and reaches success state,
   - API failure moves state to error with readable message.

4. Minimal implementation
   I created `timeline_controller.js` and moved loading/orchestration logic there. `app.js` now acts as the view binding layer and delegates state transitions to the controller.

5. Verification
   I ran the full web test suite (`npm test` in `apps/web`) and confirmed all tests pass, including the new controller tests.

### Findings and iterations

- Finding: framework alone was not enough; orchestration had to be extracted to make the architecture truly maintainable.
- Finding: controller tests made state transitions explicit and less fragile.
- Iteration: rebased remote branch updates, resolved script conflicts, reran tests, and pushed cleanly.

### Result

The FE now follows a clearer MVC-style split:
- Model: `timeline_model.js`
- Controller: `timeline_controller.js`
- View: Vue app in `app.js`

And the branch includes the incremental commits for test-first controller introduction, controller integration, and verification.
