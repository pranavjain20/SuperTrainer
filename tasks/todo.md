# SuperTrainer — Task Tracker

## v1 Planning Discussion

Everything below needs to be discussed together before building. Goal: define the path to a complete v1 a trainer could use with confidence.

- [ ] **1. Compact exercise format — visual review.** Logic + 33 tests done. On-phone design not yet reviewed. Need to check fonts, colors, spacing for exercise one-liners ("Squat: 4kg x10, 3kg x8, 3kg x8"). Decide: does the current visual pass the Equinox bar, or does it need iteration?

- [ ] **2. Live Exercise History (notebook replacement).** Scoped Mar 7 — manual search, pre-fetch last 3 sessions, compact format display. Decisions made on trigger/data/access/display. Still needs: backend endpoint design, mobile pre-fetch/caching strategy, search UX (where does it live, how does the trainer invoke it), active session banner integration. How much of this is v1-critical vs Phase 3?

- [ ] **3. Phase 2b vs Phase 3 — what's left, what's next.** Phase 2b in `docs/BUILD_PLAN.md` includes session detail view, AI flag system, swipe navigation, onboarding. Much was already built in 2a (session history, flags on entries, client profile). Diff what's done vs what's left. Then decide: finish remaining 2b items, jump to Phase 3 (Brain/RAG/patterns), or cherry-pick the highest-impact items from both?

- [ ] **4. Define the v1 scope.** What does "a trainer could use this with confidence" actually mean? Which features are must-have vs nice-to-have? What's the minimum bar before putting it in a real trainer's hands? Key principle: whatever ships must be flawless, even if not everything ships yet.

---

## Future Roadmap

### Autoresearch — Prompt Optimization Loop (Phase 3+)
- [ ] **Apply autoresearch pattern to LLM prompt optimization.** When we build briefings (Phase 3b) and the Brain (Phase 3c), design eval sets alongside the feature — then run an overnight agent loop to optimize prompts. Parser prompt is already at 100% on current eval; new AI features are where the leverage is. Pattern: agent edits prompt → runs eval → measures accuracy → keeps improvement or reverts → repeats. ~100 lines of harness code when the time comes. Reference: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

### iPad Support
- [ ] **iPad-optimized layout** — trainers may use iPads instead of physical notebooks. The app runs on iPad today (set `supportsTablet: true` in app.json), but it's a stretched phone UI. Proper iPad support means: responsive layouts (split views, sidebar navigation, wider content areas), NativeWind breakpoints (`md:`/`lg:` prefixes), and component sizing tuned for 12" screens. No backend or business logic changes needed — purely a UI/layout pass on existing components. Not urgent for v1, but should be part of the shipping plan before trainers start using it.

### Trainer Feedback — Pre-Session Briefing Requirements (from real trainer conversation)

What a trainer actually wants in the pre-session AI summary:
1. **Last same-type session recap** — if today is legs, summarize last leg session (exercises, weights, sets)
2. **Progression trends at multiple windows** — how has progression been over 3 weeks, 6 weeks, 9 weeks, 12 weeks? Not just "trending up" — specific windows.
3. **Recurring pain detection with time windows** — any recurring pain over last year, 6 months, 3 months, 6 weeks, 3 weeks? The time window matters — a pain that shows up across 3 months is different from one that appeared last week.
4. **Training gap detection** — for today's muscle group (e.g. legs), what body parts/muscle groups *haven't* been trained? Not "do this exercise" — "this part of the body hasn't been hit." The AI needs to understand muscle group coverage within a workout type, not just list exercises.
5. **Session summary (2-3 sentences)** — when browsing past sessions, the trainer wants a real summary, not a label. Three lines covering: what was done, how it went, and anything that stuck out (new pain, concern, PR, form breakdown, something worth remembering). The workout type alone is useless for recall — the trainer needs to read 3 sentences and immediately remember the session. This was initially deferred as nice-to-have but the trainer independently asked for exactly this — validates it as a core need.
6. **Compact inline format for exercise data** — trainer (15 years experience) found the table format confusing on first look. He writes "squat: 4x8, 5x8, 6x8" in his notes — that's what he reads fluently. The table is objectively cleaner but requires him to translate from his mental model. Research needed: how do trainers commonly write down sets in practice? Consider offering a compact inline view in contexts where scanning speed matters (session summaries, briefings, past session rows) while keeping the full table for detailed review and editing. The goal is matching how they already think, not teaching them a new format.
7. **Per-exercise history during live sessions (notebook replacement)** — The trainer's core workflow: right before starting an exercise (e.g. tricep pushdowns), he glances at his notebook to see what the client did last time for that specific exercise ("4kg x10, 3kg x8, 3kg x8"). Uses this to decide where to start today — "last time you fatigued early, so let's start at 4kg again." This happens for EVERY exercise, not just the first one. It's pre-exercise, not pre-session. The history also stays accessible mid-exercise if the client asks "what did we do last time?" The app must replicate the speed of glancing at a notebook — if it takes multiple taps or scrolling, the trainer won't use it and will just rely on (unreliable) memory. This is the strongest validation yet for the compact format: the trainer needs to read "4x10, 3x8, 3x8" at a glance, mid-coaching, then look back up. Two open questions: (a) how does the app know which exercise to surface history for — reactive (voice clip triggers it), manual (trainer searches), or hybrid? (b) how many previous sessions to show — last session is essential, last 2-3 would show progression trends.
