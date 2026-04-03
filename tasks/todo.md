# SuperTrainer — Task Tracker

## v1 Scope — FINALIZED (Apr 3, 2026)

**v1 target:** Replace the trainer's notebook. Competitors: physical notebook, GoodNotes on iPad, Notes app on iPhone, and trainers who use nothing (just memory). Must be simpler, cleaner, and faster than all of them.

**v1 = Notebook Replacement + Intelligence Layer.** The notebook replacement makes the core loop work. The intelligence layer is what makes us better than paper.

**What the notebook does (what we replace):**
- Before session: check plan (if exists), check last time's numbers
- During session, before each exercise: glance at last time's numbers for that exercise
- During session, during/after each set: record numbers in real time (weight, reps)
- During session: modify the plan on the fly if things change
- Before next session (sometimes): write a plan

**What makes us better:** Voice captures everything — numbers AND the notes/observations a trainer would never write down. Intelligence comes for free (briefings, pain tracking, flags) with zero extra effort.

---

### Tier 1 — Notebook Replacement (must ship)

Build order: top to bottom (dependencies flow downward).

- [ ] **1. Compact exercise format — visual review.** Logic + 33 tests done. Need on-phone visual check before anything else. Prerequisite for live history.
- [ ] **2. Live exercise history.** Before each exercise, see what client did last time. The #1 daily action — happens 8-15 times per session. Must be faster than flipping a page in GoodNotes.
- [ ] **3. Plan creation from app.** Create a plan via voice or text. Backend CRUD exists, no mobile UI.
- [ ] **4. Plan modification on the fly.** Change the plan mid-session when things change.
- [ ] **5. End-session plan dictation.** "Anything for next time?" -> saves as plan for next session.
- [ ] **6. Settings (weight units).** US trainers need lbs. No settings screen exists yet.

### Tier 2 — Intelligence Layer (what makes us better than a notebook)

- [ ] **7. Session summaries.** 2-3 sentence AI recap per session. When browsing history, trainer reads 3 lines and remembers the session.
- [ ] **8. Flag system (AI auto-assign).** Green/yellow/red flags on session save. Display exists, no AI assignment logic.
- [ ] **9. Pre-session briefing.** 4-layer AI summary before each client arrives. The "why is this better than a notebook" moment.

### Conditional

- [ ] **10. Session detail view.** Decide after compact format visual review — if expandable cards feel cramped with compact format, pull this into v1.

### Deferred — Not in v1

- **Onboarding flow** — manual setup for single trainer beta
- **Auth** — single user, not needed yet
- **The Brain** — post-v1, build with real data from actual trainer usage
- **Pattern detection** — post-v1, feeds into briefings later
- **Push notifications** — post-v1
- **Swipe navigation** — post-v1
- **Home screen flag indicators** — post-v1
- **Plan vs actual comparison** — post-v1
- **Progress charts** — post-v1
- **iPad layout** — post-v1

---

## Future Roadmap

### Autoresearch — Prompt Optimization Loop (Phase 3+)
- [ ] **Apply autoresearch pattern to LLM prompt optimization.** When we build briefings and the Brain, design eval sets alongside the feature — then run an overnight agent loop to optimize prompts. Parser prompt is already at 100% on current eval; new AI features are where the leverage is. Pattern: agent edits prompt -> runs eval -> measures accuracy -> keeps improvement or reverts -> repeats. ~100 lines of harness code when the time comes. Reference: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

### iPad Support
- [ ] **iPad-optimized layout** — trainers may use iPads instead of physical notebooks. The app runs on iPad today (set `supportsTablet: true` in app.json), but it's a stretched phone UI. Proper iPad support means: responsive layouts (split views, sidebar navigation, wider content areas), NativeWind breakpoints (`md:`/`lg:` prefixes), and component sizing tuned for 12" screens. No backend or business logic changes needed — purely a UI/layout pass on existing components.

### Trainer Feedback — Pre-Session Briefing Requirements (from real trainer conversation)

What a trainer actually wants in the pre-session AI summary:
1. **Last same-type session recap** — if today is legs, summarize last leg session (exercises, weights, sets)
2. **Progression trends at multiple windows** — how has progression been over 3 weeks, 6 weeks, 9 weeks, 12 weeks? Not just "trending up" — specific windows.
3. **Recurring pain detection with time windows** — any recurring pain over last year, 6 months, 3 months, 6 weeks, 3 weeks? The time window matters — a pain that shows up across 3 months is different from one that appeared last week.
4. **Training gap detection** — for today's muscle group (e.g. legs), what body parts/muscle groups *haven't* been trained? Not "do this exercise" — "this part of the body hasn't been hit." The AI needs to understand muscle group coverage within a workout type, not just list exercises.
5. **Session summary (2-3 sentences)** — when browsing past sessions, the trainer wants a real summary, not a label. Three lines covering: what was done, how it went, and anything that stuck out (new pain, concern, PR, form breakdown, something worth remembering). The workout type alone is useless for recall — the trainer needs to read 3 sentences and immediately remember the session.
6. **Compact inline format for exercise data** — trainer (15 years experience) found the table format confusing on first look. He writes "squat: 4x8, 5x8, 6x8" in his notes — that's what he reads fluently. The goal is matching how they already think, not teaching them a new format.
7. **Per-exercise history during live sessions (notebook replacement)** — The trainer's core workflow: right before starting an exercise, he glances at his notebook to see what the client did last time for that specific exercise. This happens for EVERY exercise, not just the first one. The app must replicate the speed of glancing at a notebook.
