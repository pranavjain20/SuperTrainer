# SuperTrainer — Current Status

**Last updated:** Mar 10, 2026
**Current phase:** Phase 2a — Mobile App. COMPLETE. Design system polish done.
**Next action:** (1) Review business pitch document (`docs/PITCH.md`), (2) review compact exercise format design on phone, (3) plan + build live exercise history feature (scoped — see below), (4) planning discussion — diff 2b vs what's already built, decide next phase. Phase 2a walkthrough guide written (`docs/guides/phase-2a.md`). Columbia AI startup submission reviewed (Mar 9). iPad support added to future roadmap (Mar 10).

---

## Business Pitch Document — ADDED (Mar 8, 2026)

Created `docs/PITCH.md` — standalone pitch with market data and sourced statistics. Core thesis: consumers are adopting AI fitness fast (61% of gym members), but only 10% would go AI-only. Trainers feel threatened but lack tools. SuperTrainer enables trainers instead of replacing them. All stats traced to original sources (ABC Fitness, Les Mills, YouGov, Stanford) with caveats noted. Article screenshot saved to `reference/`.

---

## Live Exercise History — Scoped (Mar 7, 2026)

**The problem:** During a session, before each exercise, the trainer checks what the client did last time for that specific movement. Uses compact format ("4kg x10, 3kg x8, 3kg x8") to decide today's programming. This is pre-exercise, not pre-session — happens for every movement. The app must surface this as fast as flipping back three pages in a notebook.

**Brainstorming decisions (Mar 7):**

- **Trigger: Manual search only.** Voice-reactive ruled out — trainer records clips after finishing an exercise, not before, so the timing is wrong. Also expensive (every lookup would hit the LLM pipeline). Chatbot queries ruled out for the same reasons — slower than a notebook and more costly.
- **Data strategy: Pre-fetch at session start.** When the trainer opens a session, pull the last 3 sessions' worth of entries for that client. All data lives locally on device. Search is instant, no network round-trip mid-session. The data is small (30-50 exercise entries across 3 sessions).
- **Access: Session-wide, not locked to recording screen.** Trainer moves around the app during a session (client profile, other tabs). The active session banner already follows them across tabs. Exercise history lookup should be available from anywhere during an active session.
- **Display: Compact format** ("4kg x10, 3kg x8, 3kg x8") — utility functions already built.
- **Session depth: Last 3 sessions.** Covers most training frequencies. Not tied to workout type (since plans can change day-of).

**Future enhancement (Phase 3 — session planning):**
- When a session plan exists, auto-surface history for the planned exercises (no manual search needed).
- Manual search remains as fallback for when the trainer pivots mid-session ("planned legs, switching to upper body").
- The plan-linked version is a layer on top of the general-purpose lookup, not a replacement.

**The narrative to keep in mind:** A notebook is three pages — flip back, scan for "squats," see the numbers. Done in seconds. The app has to be that easy and that intuitive. If it takes more taps or more time than flipping pages, the trainer won't use it.

---

## Compact Exercise Format — IN PROGRESS (Mar 4, 2026)

Added compact exercise lines to client profile session cards (3-level expand: collapsed → summary → full detail). Backend logic and tests complete (33 new mobile Jest tests). Jest test runner set up for mobile project. **Design needs polish** — first task next session is reviewing the visual design before proceeding to planning.

Files changed: `sets.ts` (formatCompactExercise, formatCompactSet, convertWeight), `sessions.ts` (classifyWorkoutFromEntries), `useClient.ts` (useClientEntries, groupEntriesBySession), `[id].tsx` (3-level card view), `sets.test.ts` (new). New: `jest.config.js`, test script in package.json.

---

## Design System Polish — COMPLETE (Mar 1, 2026)

Centralized the entire mobile app's visual language before moving to the next phase. Replaced ad-hoc color strings and inline font styles with a token system + ThemedText component. All 40+ components migrated. Key improvements:
- **tokens.ts:** semantic color palette, typography scale (display → caption), spacing primitives
- **ThemedText:** variant-based text component replacing raw Text + inline styles
- **Inter + JetBrains Mono** font family (6 files) replacing SpaceMono
- **SessionRow density:** 3-line ~130px → 2-line ~80px compact layout, client name as hero
- **Section headings:** "Workout Summary" / "Workout Details" bumped from caption to title-3
- **Home screen spacing:** consistent padding above and below session card list
- **EndTimePickerSheet:** extracted to its own component
- **Backend:** timezone-aware date filtering for session list endpoint
- 734 backend tests passing, phone-tested all core flows

---

## Phase 2a: Mobile App — COMPLETE

### Pre-Work: Backend Addition ✅ COMPLETE

Added `GET /api/v1/sessions` — trainer-level session listing with optional `scheduled_for_date` query param. Filters by `scheduled_for` OR `started_at` matching the date (so ad-hoc sessions without `scheduled_for` still appear). 8 new tests, 691 total backend tests passing.

### Day 1: Project Setup + Tab Navigation ✅ COMPLETE

**SDK:** Expo SDK 54 (SDK 55 too new for Expo Go on App Store). React 19.1, RN 0.81.5, Reanimated v4, Expo Router v6.
**Styling:** NativeWind v4 (Tailwind for RN) — configured and working, no issues.
**Dependencies:** TanStack Query v5, Zustand v5, expo-av (audio), expo-haptics.
**Navigation:** Four-tab layout (Home, Clients, Brain, Session). Clients and Session tabs have their own stack navigators for nested navigation.
**Root layout:** QueryClientProvider wrapping entire app, splash screen handling, font loading.
**Verified:** App runs on physical phone via Expo Go. Fast Refresh working — edit file, save, phone updates in ~1 second.
**Concepts doc:** `concepts/phase-2-day-1.md` — React, React Native, Expo, file-based routing, NativeWind, TanStack Query, Zustand.

### Day 2: API Client + TypeScript Types ✅ COMPLETE

Full API layer mirroring backend. `src/api/types.ts` — all TypeScript interfaces (enums, generic wrappers, all 10 models, create/update variants, SetData union handling both seed and voice pipeline formats). `src/api/client.ts` — fetch wrapper with apiGet/apiPost/apiPatch/apiDelete/apiUpload and custom ApiError class. Five endpoint modules: `clients.ts`, `sessions.ts`, `entries.ts`, `plans.ts`, `voice.ts`. Config updated with dev machine IP.

### Day 3: Home Screen + Client List ✅ COMPLETE

**Home screen:** Today's sessions with time, client name (enriched client-side via useClientMap), status badge (Done/In Progress/Countdown/Upcoming), duration. Pull-to-refresh. Empty state: "No sessions today — Enjoy your rest day!"
**Clients screen:** Full client list grouped alphabetically by first letter. Real-time search (case-insensitive). Active client count. Pull-to-refresh.
**Components:** ClientRow (initials avatar with deterministic color hash), SessionRow (status badge logic), LoadingState, ErrorState (with retry), EmptyState.
**Hooks:** useClients (sorted A-Z, 200 limit, 5min stale), useClientMap (O(1) lookups from same cache), useTodaySessions (client enrichment, time sorting).
**Utils:** `dates.ts` (formatTime, formatDayHeader, formatMemberSince, toISODateString), `initials.ts` (deterministic initials + color from name).

### Day 4: Client Profile ✅ COMPLETE

`app/(tabs)/clients/[id].tsx` — 491-line client profile screen with three-tab layout. **Header:** initials avatar, name, "Training since" date. **Overview tab:** goals (styled pills) + injury history (split on periods). **Sessions tab:** expandable session cards — tap to reveal all entries (exercises + observations), loaded on-demand via TanStack Query, cached by session ID. ExerciseCard shows set table (reps/weight/RPE/notes), handles both seed format (`weight_kg`) and voice pipeline format (`weight`). ObservationCard shows colored left border by flag_color with flag reason header. **Plans tab:** plan cards with date header and numbered lines.
**Hooks:** useClient (single client, 5min stale), useClientSessions (limit 20, 2min stale), useClientPlans (limit 20, 5min stale).

### Day 5: Session Screen + Record Button ✅ COMPLETE

**Session recording workspace** — the core UX where trainers record voice clips during sessions.
**New files (5):** `useSession.ts` (single session query, 60s stale), `useVoiceRecorder.ts` (expo-av recording lifecycle: permission → record → stop → URI, cleanup on unmount), `RecordButton.tsx` (80px animated button with pulse ring, haptic feedback, MM:SS duration display), `[sessionId].tsx` (recording screen: header with client name/time/status, empty timeline placeholder, bottom record bar), `recordingStore.ts` (Zustand store for cross-component recording state).
**Modified files (3):** `session/index.tsx` (replaced placeholder with session list using useTodaySessions), `session/_layout.tsx` (registered [sessionId] route), `(tabs)/index.tsx` (wired home screen session tap → recording screen).
**Recording navigation guards:** Zustand store shares isRecording + stopRecording across components. Back button shows Alert confirmation. Tab layout intercepts all non-session tab presses when recording is active — "Keep Recording" or "Stop & Leave" (stops recording, then navigates). Session tab unguarded.
**Animation:** RN built-in Animated API (not Reanimated — version mismatch with Expo Go). Button springs to 1.25x via `Easing.out(Easing.back(1.4))`. Pulse ring loops at 2x scale, 0.5→0 opacity, 1400ms, with 0-duration reset step.
**Audit fixes:** Record button disabled for completed sessions, missing `setGlobalRecording` deps in useCallback arrays.
**Note:** Recording only — Day 6 wires `processVoiceClip()` to send audio to backend.

### Days 6-7: Voice Pipeline + Inline Editing ✅ COMPLETE

**Day 6 — Voice clip upload pipeline:**
`sessionStore.ts` (Zustand) for processing state + error tracking. `useVoiceClipUpload` hook wiring expo-av recording → backend voice endpoint → TanStack Query cache invalidation. `useSessionEntries` hook for live timeline updates. `Timeline` component with auto-scroll, processing indicator, error retry row. Cards split into standalone components: `ExerciseCard` (set table with headers), `ObservationCard` (flag-colored accent), `EntryCard` (type-based dispatch).

**Day 7 — Tap-to-edit on any card:**
`ExerciseEditModal` — bottom sheet with editable exercise name + per-set reps/weight/RPE/notes. `ObservationEditModal` — text area + flag color picker (green/yellow/red). `useEntryMutations` with `setQueryData` for instant cache updates (no flicker). `useEditableEntries` shared hook used by both Timeline and client profile's ExpandableSessionCard. Exercise numbering (1, 2, 3...) on cards. `PressableCard` wrapper, `strings.ts` utilities (DRY extractions).

**Backend fixes:** Parser rules hardened (never hallucinate content, never assume bodyweight). `entry_service.update_entry` now recalculates `total_volume_kg` when sets change. `getSetWeight` reads `weight` before `weight_kg` (voice format priority). 3 new backend tests. **694 total backend tests passing.**

### Day 8: Cross-Tab Navigation + Session Flow Polish ✅ COMPLETE

Recording screen moved to root level (`/recording/[sessionId]` above all tabs) — `router.back()` returns to wherever you came from. Tab bar hidden during recording. Swipe-back dynamically disabled while recording (via `useRecordingStore` in root layout). Session list UX overhaul: in-progress sessions show green pill + blue "CONTINUE SESSION" button, future sessions show countdown, completed sessions show "DONE" + duration. Custom back buttons on all screens. `ConfirmSheet` component. Timeline auto-scroll fix (only on new entries, not initial load).

**Files changed:** 14 files (3 created, 1 deleted, 10 edited). **694 backend tests passing.**

### Day 9: End Session Flow + UX Polish ✅ COMPLETE

Server-side duration computation (`ended_at - started_at`). Post-session flow: summary card + Workout Details container card + Done button. `useEndSession` hook. Client profile expandable sessions now show workout type (classify on expand, cached forever). Structured SUMMARY block with TYPE/DURATION/EXERCISES/SETS. Systematic typography hierarchy. Dead code cleanup (deleted PlanInput.tsx, unused functions).

**Backend:** Plan-session FK linking with ownership validation. 14 new integration tests. **725 total backend tests.**

### Day 10: Golden Audit (Days 6-10) ✅ COMPLETE

**5 audit findings fixed:**
1. **BUG — Completed sessions hidden:** `useSessions.ts` filtered out ended sessions. Removed the filter — completed sessions now show with "Done" pill.
2. **TYPE SAFETY — ObservationEditModal unsafe cast:** `SessionEntryUpdate` didn't allow `null` for `observation_text`, `flag_color`, `flag_reason`. Added `| null` to the type, removed `Record<string, unknown>` cast.
3. **DRY — Exercise numbering repeated 3x:** Same `let exerciseCount = 0; entries.map(...)` pattern in Timeline, recording screen, client profile. Extracted `numberExercises(entries)` utility returning `Map<string, number>`.
4. **DRY — Session header duplicated:** ~80% identical header in ended vs active recording screen. Extracted `SessionHeader` component with optional END SESSION button.
5. **TEST GAP — Classifier threshold boundary:** No test at exactly 70% (boundary) or below. Added `test_at_threshold_boundary` (7/10 = 70% → classifies) and `test_below_threshold` (2/3 = 67% → Full Body).

**Dependency fix:** `lines-and-columns` added to package.json (required by `sucrase` via NativeWind/Tailwind — was missing after node_modules rebuild).

**Verification:** 727 backend tests passing (725 + 2 new). TypeScript clean (only pre-existing @expo/vector-icons module declaration from Expo bundler). Staff engineer re-read of all changed files.

### Day 11: Phone Testing + UX Fixes ✅ COMPLETE

All 7 test phases passed on physical iPhone via Expo Go. 12 UX fixes applied live during testing:
- Workout classifier bug: `goblet_squat` vs `Goblet Squat` underscore mismatch (one-line fix in `workout_classifier.py`)
- Dropped "Sets" from session summary, "Summary" → "Workout Summary"
- Exercise name sizing 17px/700 → 15px/600
- Removed yellow highlighting on set notes
- Goal/injury pill capitalization
- Observations now require flag_color (green/yellow/red, no null) — parser schema + prompt updated
- Seed data observations for Sarah Chen flagged yellow
- Empty session shows "No exercises recorded"
- In Progress pill orange (was green, same as Done)
- Status pill sizing matched to Continue Session button
- Record button 400ms debounce

**727 backend tests passing.**

### Day 12: Final UX + Merge to Master ✅ COMPLETE

**Active session banner:** `ActiveSessionBanner` component renders in tab layout when a session is recording — shows client name + elapsed time, taps to navigate back to recording screen. Persistent across all tab navigation.

**Clarification UX:** `ClarificationModal` prompts trainer to confirm/correct when parser returns low-confidence results. `ManualEntryModal` for hand-typing exercises/observations when voice doesn't capture it. Timeline updated to render clarification prompts inline.

**Voice pipeline backend:** Parser returns confidence metadata, voice service handles `clarification_needed` status, new schema fields. 207 lines of new backend tests.

**Merge:** Squash merged 19 commits (Days 1-12) to master. 734 backend tests passing. 96 files, 21k lines added.

---

## Phase 1a: Backend Foundation — COMPLETE

Documentation phase is complete. All 6 docs reviewed and approved. CLAUDE.md pre-work fix applied (line 14: "6-phase (13 sub-phase) build plan").

### What Exists Today (v1 code being replaced)

- 7 models in `models.py` (Trainer, Client, Session, ExerciseLog, InjuryFlag, ClientAnalysis, Exercise)
- Schemas in `schemas.py` for all 7 models
- 4 API route files: `clients.py`, `sessions.py`, `exercise_logs.py`, `injury_flags.py`
- Service layer: `client_service.py`, `session_service.py`, `exercise_log_service.py`, `injury_flag_service.py`
- `conftest.py` with truncation-based test isolation
- 1 Alembic migration (`c1e38ab066d1_initial_models.py`)
- Error handling middleware + request logging middleware in `main.py` (keep as-is)
- Seed script with 1 trainer, 5 clients, 20 sessions
- 93 tests (these will break and be rewritten)

### What Changes v1 → v3

| v1 | v3 | Change |
|----|-----|--------|
| ExerciseLog | SessionEntry | Replace (unified timeline with entry_type enum) |
| — | SessionPlan | New model |
| — | BrainConversation | New model |
| — | BrainMessage | New model |
| Session | Session | Add `scheduled_for`, `plan_id` FK |
| ClientAnalysis | ClientAnalysis | Add `client_score`, `score_breakdown` |
| InjuryFlag | InjuryFlag | Change FK: `exercise_log_id` → `session_entry_id` |

---

## Day-by-Day Plan

### Day 1: Models + Migration ✅ COMPLETE

**Goal:** Rewrite all models, create fresh migration, basic model tests.

**Files to modify:**
- `backend/app/models.py` — Rewrite with all 10 models
- `backend/alembic/versions/c1e38ab066d1_initial_models.py` — Delete
- New migration via `alembic revision --autogenerate -m "v3_all_models"`

**Model changes:**
1. **Trainer**: add `supabase_user_id` (nullable String, Phase 4 placeholder)
2. **Client**: update relationships (session_entries replaces exercise_logs)
3. **Session**: add `scheduled_for` (DateTime, nullable), `plan_id` (FK → session_plans, nullable)
4. **SessionEntry** (replaces ExerciseLog): add `entry_type` enum (exercise_card | observation_card), `sequence_order` (Integer), keep all exercise fields, add observation fields (`observation_text`, `attached_to_set`, `flag_color`, `flag_reason`)
5. **SessionPlan** (new): `client_id`, `trainer_id`, `plan_text`, `planned_for_date`
6. **InjuryFlag**: `session_entry_id` replaces `exercise_log_id`
7. **ClientAnalysis**: add `client_score` (Float, 0-100), `score_breakdown` (JSONB)
8. **Exercise**: keep as-is
9. **BrainConversation** (new): `trainer_id`, `title`, timestamps
10. **BrainMessage** (new): `conversation_id` (FK), `trainer_id`, `role` (user|assistant), `content`

**pgvector:** Enable extension in migration. Add Vector embedding columns to: sessions.raw_transcript, session_entries.observation_text, session_entries.form_notes, session_plans.plan_text. Note: requires `pgvector` Python package in requirements.txt.

**Tests:** Write model creation + query tests for all 10 models (~10-15 tests).

**End of day:** All models migrate cleanly, basic create/query works for each model.

**Result:** 10 models, 5 enums, 4 Vector columns, fresh migration, 22 tests (all passing). On branch `feat/phase-1a-backend`.

### Day 2: Schemas + Schema Tests ✅ COMPLETE

Rewrote `schemas.py` for all 10 v3 models (34 Pydantic classes). Deleted old ExerciseLog schemas. Added SessionEntry with `@model_validator` for cross-field validation (exercise_card vs observation_card). Added InjuryFlagUpdate, SessionPlan, BrainConversation, BrainMessage, ClientAnalysis, Exercise schemas. Fixed `sets` type from `list | dict | None` to `list[dict] | None`. 57 pure validation tests, 3 audit passes caught 7 gaps. Added Code Quality Philosophy section to CLAUDE.md.

**Result:** 34 schema classes, 57 schema tests + 22 model tests = 79 total, all green.

### Day 3: Client + Session CRUD ✅ COMPLETE

Deleted 4 v1 files (exercise_logs.py, exercise_log_service.py, test_exercise_logs.py, test_injury_flags.py). Fixed main.py (removed exercise_logs_router). Fixed injury_flags.py (session_entry_id validation). Added plan_id FK validation to sessions.py. Rewrote conftest.py with HTTP client + trainer fixtures. Rewrote test_clients.py (20 tests) and test_sessions.py (19 tests). Cleaned Co-Authored-By lines from 2 old commits, force-pushed clean history.

**Result:** 124 total tests (22 model + 57 schema + 20 client + 19 session + 4 error handling + 2 health), all green.

### Day 4: Session Entry CRUD ✅ COMPLETE

Created entry_service.py (7 functions), entries.py router (6 endpoints, 3 URL paths), 54 integration tests. Schema changes: removed session_id from SessionEntryCreate (comes from URL path), made sequence_order optional (auto-calculated). Trainer ownership validated on every endpoint — first router to do this properly. Audit caught: unused import, missing return types, missing PATCH validation tests (sequence_order=0, empty name, negative volume), missing cross-trainer PATCH/DELETE ownership tests.

**Result:** 178 total tests (22 model + 58 schema + 20 client + 19 session + 54 entry + 4 error handling + 2 health - 1 overlap), all green.

### Day 5: Session Plan + Injury Flag CRUD ✅ COMPLETE

Created plan_service.py (5 functions), plans.py router (5 endpoints across 2 URL paths), 28 tests. Completed injury_flag_service.py (added get/update/delete), rewrote injury_flags.py with ownership validation on all endpoints + 3 new endpoints (GET/PATCH/DELETE), 37 tests. Added SessionPlanListResponse to schemas.py. Registered plans router in main.py. Audit caught: missing return type annotations on helper functions, 2 untested ownership paths (PATCH wrong trainer, list wrong trainer's client).

**Result:** 243 total tests (22 model + 58 schema + 20 client + 19 session + 54 entry + 28 plan + 37 injury flag + 4 error handling + 2 health - 1 overlap), all green.

### Day 6: Seed Script ✅ COMPLETE

Full rewrite of `seed.py` for v3 schema. Replaced broken ExerciseLog imports with SessionEntry. Eliminated raw `Session.__table__.select()` hacks — uses ORM object references throughout. 5 clients with realistic profiles: Sarah (1 session, assessment), Marcus (3, powerlifter), Aisha (5, post-pregnancy), Jake (10, beginner), Elena (15, elderly). 34 sessions, 115 session entries (exercise_card + observation_card mix), 19 canonical exercises, 6 session plans, 4 injury flags (1 resolved). Idempotent via TRUNCATE CASCADE. 10 seed tests covering counts, relationships, plan linking, injury validation, resolved flag, and idempotency.

**Result:** 272 total tests (262 existing + 10 seed), all green. Feature branch pushed to remote.

### Day 7: Edge Cases + Integration Tests ✅ COMPLETE

Fixed plan-client mismatch bug in session create (could attach Client A's plan to Client B's session → now 422). Added `duration_minutes ge=0` validation to SessionUpdate. Created `test_integration.py` (8 tests: entry delete → flag SET NULL via API, archived client child access for 4 entity types, sequence order after deletion, plan-client mismatch, non-existent session_entry_id on flag create). Created `test_edge_cases.py` (12 tests: empty PATCH `{}` for all 5 entities, pagination edge cases limit=0/limit=-1/stale cursor, cross-type contamination documented, pain_level=11 upper bound, negative duration_minutes).

**Result:** 292 total tests (272 existing + 20 new), all green.

### Day 8: Coverage Audit + Polish ✅ COMPLETE

Fixed 3 missing `ondelete="CASCADE"` on trainer FK columns (Session.trainer_id, BrainMessage.trainer_id, SessionPlan.trainer_id DB sync). Added Alembic migration. Consolidated 3 duplicate ownership validators into dependencies.py (5 validators in one file). Replaced `response_model=dict` with typed `DataResponse[XResponse]` on all 14 single-resource endpoints. Fixed injury_flags tag inconsistency (dashes → underscores). Cleaned unused imports. 3 new integration tests.

**Result:** 295 total tests (292 existing + 3 new), all green. 2 Alembic migrations.

### Day 9: End-of-Phase Audit ✅ COMPLETE

Three exploration agents read every source file, test file, and infrastructure file. Found and fixed 1 real bug + 1 data integrity gap + 1 trivial annotation. Fixed cross-type contamination on PATCH /entries (exercise_card accepting observation_text without entry_type in payload → now 422 at route level). Added resolved_at validation on InjuryFlagUpdate (rejects resolved_at without resolved=true). Added return type to health_check(). All exit criteria met.

**Result:** 301 total tests (295 existing + 6 new), all green. All exit criteria checked off.

### Day 10: Golden Audit + Phase Completion ✅ COMPLETE

Day 10 golden audit (covering Days 6-10). Extracted pagination helper — 5 services had identical ~20-line cursor pagination blocks, now use a single `paginate()` function. Fixed alembic/env.py to read DATABASE_URL from settings instead of hardcoded localhost. Fixed plan_service to allow nulling planned_for_date. Added 5 tests (empty sets, empty goals, null date PATCH, error response structure). Two audit agents read every source and test file — no hacks, no over-engineering, no deferred work found. Squash merged to master.

**Result:** 306 total tests, all green. Phase 1a merged to master as single commit.

---

## Phase 1a Exit Criteria

- [x] 10 models in models.py, all with correct fields and relationships
- [x] pgvector enabled, embedding columns present
- [x] Fresh Alembic migration runs clean
- [x] All Pydantic schemas validate correctly
- [x] Client CRUD: list, create, get, update, archive — all tested
- [x] Session CRUD: create, get, list, update, delete — all tested
- [x] Session Entry CRUD: create (both types), list by session, list by client — all tested
- [x] Session Plan CRUD: create, get, list, update — all tested
- [x] Injury Flag CRUD: create, list by client — all tested
- [x] Seed script: 5 clients, 1/3/5/10/15 sessions, varied data — runs clean
- [x] ~60-80+ tests all passing (306 tests)
- [x] Swagger docs show all endpoints
- [x] No 500s for any bad input (all proper 4xx)
- [x] Cross-entity ownership validated everywhere
- [x] Cascade deletes work and are tested
- [x] Error format consistent: `{"error": {"code": "...", "message": "..."}}`
- [x] End-of-phase audit completed honestly

---

## Phase 1b: Voice Pipeline

**Goal:** Trainer speaks into phone → audio transcribed by Deepgram → Claude parses transcript into structured exercise/observation cards via tool_use → validation normalizes data → structured entry returned in ≤3 seconds.

First AI-heavy phase. Server is stateless — phone sends full session context with each clip.

### Four Components

1. **Deepgram service** — Speech-to-text. Sends audio + keyterm list (100 exercise names), gets back transcript. Black-box API, minimal custom logic.
2. **Claude parser service** — Takes transcript + session context, uses tool_use to output structured JSON matching SessionEntry model. Classifies intent (new exercise, additive, observation, etc). 80% of engineering effort (prompt design, testing, iteration).
3. **Validation layer** — Post-processing. Fuzzy-matches exercise names to canonical DB, normalizes weight units to kg, expands "3 sets of 10" into individual set records, extracts pain reports with body part mapping.
4. **Voice clip endpoint** — `POST /sessions/{id}/voice-clip`. Ties Deepgram → parser → validation into one API call. Returns structured entry + processing time breakdown.

### Day-by-Day Plan

#### Day 1: Exercise Database + Deepgram Service ✅ COMPLETE

**Mode:** Claude drafts, Pranav researches exercises.

- [x] Created `exercise_db.json` — started at 97 exercises, Pranav researched and rebuilt to 142 exercises with 3,466 aliases, 706 expert common_errors, specific anatomy (115 unique muscle terms)
- [x] Built `services/transcription.py` — load_exercise_db(), build_keyterm_list(), transcribe_audio()
- [x] Added `deepgram-sdk>=3.0,<4.0` to requirements.txt
- [x] Updated `seed.py` to load from JSON (dynamic column introspection)
- [x] Created `tests/test_transcription.py` — 24 tests (DB loading, keyterm building, Deepgram mocked)
- [x] Created `tests/test_exercise_db.py` — 36 tests (comparative metrics, trainer speech recognition, structural quality, keyterm coverage)
- [x] Updated `tests/test_seed.py` exercise count assertions (dynamic)
- [x] Documented heuristic decisions pending real-data validation (keyterm priority, skip terms, abbreviation detection, upcoming parser decisions)
- [x] 366 total tests passing (306 Phase 1a + 60 new)

#### Day 2: Claude Parser — Tool Schema + Core Parsing ✅ COMPLETE

**Mode:** Collaborative (first AI-heavy day, Pranav learned tool_use end-to-end).

Built `services/parser.py` incrementally — concept-by-concept with Pranav making design decisions. Two tool schemas (`record_exercise_card` + `record_observation_card`) where the tool name IS the classification. 10-rule system prompt. Frozen dataclasses (`ParsedSet`, `ParsedExerciseCard`, `ParsedObservationCard`, `ParserResult`). Created `concepts/2026-02-24.md` — comprehensive learning document covering tool_use, token generation, vertical AI moat, intelligence split, mocking patterns. Audit agent found 4 real issues (malformed set KeyError, untested mixed fields, unknown tool names, flag_reason gap). Staff engineer review found 2 more (unused imports, missing edge case test).

**Result:** 396 total tests (366 existing + 30 new parser tests), all green.

#### Day 3: Parser — Intent Classification + Additive Parsing + Context ✅ COMPLETE

**Mode:** Collaborative.

Built session context formatting (`format_session_context()` + helpers) — prior entries formatted as numbered readable text ([1], [2]) in user message. Added `modify_exercise_card` as third tool — target_entry_id for referencing context entries, action ("add"/"correct") for merge behavior, target_sets for set-level targeting. Five new system prompt rules (11-15) covering intent routing, no modify without context, ambiguity handling, modify scope, conservative correction. Pranav contributed key edge cases: trainer re-statement (records sets individually then summarizes), conservative replace (don't overwrite unless explicitly correcting). Product decision logged for Day 5: parser ambiguity flags must not become observation cards — return as `clarifications_needed` in API response instead.

**Result:** 433 total tests (396 existing + 37 new), all green.

#### Day 4: Validation Layer ✅ COMPLETE

**Mode:** Independent.

Built `services/validation.py` in two passes. First pass: exercise fuzzy matching (rapidfuzz WRatio against 142-exercise DB with 3,466 aliases), weight normalization (lbs→kg), set validation, pain extraction (keyword + body part + severity mapping), card validators, and orchestration. Second pass: hardening for real trainer speech — word-boundary regex (eliminated "pulldown"/"reached" false positives), 30 new pain keywords (sounds, states, colloquial, sensations), 33 new body parts (spine, muscles, joints, digits), 10 new severity modifiers, negation handling ("no knee pain" skipped), comma clause splitting, suspicious value warnings. Added `preferred_weight_unit` to Client model (Literal["kg", "lbs"], default "kg") for per-client weight unit defaults — trainers with clients in different countries need this.

- [x] `services/validation.py` — fuzzy match, weight normalization, pain extraction, card validators
- [x] Validation hardening — word boundary regex, negation, comma splitting, expanded keywords/body parts/modifiers, suspicious value warnings
- [x] Per-client `preferred_weight_unit` — model column, schema fields, migration, 4 client tests
- [x] Add `rapidfuzz` to requirements.txt
- [x] 119 validation tests + 4 client tests = 552 total tests passing

**Result:** 552 total tests (433 existing + 115 validation + 4 client), all green.

#### Day 5: Voice Clip Endpoint + Integration Tests ✅ COMPLETE

**Mode:** Independent, Pranav reviews.

Built `services/voice.py` (orchestration service) and `api/voice.py` (endpoint). Pipeline: audio upload → Deepgram transcription → Claude parser → validation → DB persistence. Returns structured entries + timing breakdown. Clarification handling: yellow-flagged observations returned as `clarifications_needed` (not persisted). Added `VoiceClipResponse`, `TimingBreakdownResponse`, `ClarificationItem`, `ValidationWarningResponse` schemas. Registered voice router in main.py. Added `python-multipart` dependency.

42 tests (15 integration + 27 hardening): happy path, modification updates, clarifications not persisted, non-yellow observations persisted, 404/422 error paths, empty transcript, timing fields, warnings propagation, fuzzy match. Hardening: 12 helper unit tests (_entry_to_context_dict, _validated_set_to_db_format, _build_modification_kwargs), 3 weight unit tests (lbs→kg conversion, kg passthrough, None defaults), 6 modification edge cases (targeting observation, form_notes/cues append, target_sets subset, out-of-range, weight correction), 3 mixed content clips (exercise+observation, exercise+clarification, exercise+modification), 3 data integrity (sequence_order, volume, canonical match).

**Result:** 594 total tests (552 existing + 42 new), all green.

#### Day 15 Golden Audit (Days 1-5 Checkpoint) ✅ COMPLETE

Three audit agents read every Phase 1b source and test file (~5,000 lines). Most findings were false positives dismissed after manual verification. Five real issues fixed: normalize_weight() now warns on unknown units instead of silently defaulting to kg; test_lookup_size verifies all 142 canonical names present (not just len > 3000); parser handles malformed Claude responses (empty input {}) gracefully; added modification field preservation test; removed unused type declaration in voice.py.

**Result:** 598 total tests (594 existing + 4 new), all green.

#### Day 6: Set-Level Observation Attachment + Temporal Context ✅ COMPLETE

**Mode:** Most collaborative day yet. Pranav attended a real training session, brought back transcript + test cases.

Built set-level observation attachment — observation cards can now target a specific exercise entry and set from the session context. Two new optional fields (`target_entry_id`, `attached_to_set`) threaded through parser → validation → persistence. `target_entry_id` is transient (used for validation, not stored); `attached_to_set` persists to the existing DB column.

Key distinction implemented via prompt rules 19 + 22: during-exercise speech ("lower back pain on set 3 of deadlifts") gets attached; between-exercise speech ("his lower back is hurting") stays session-level. Rule 23 adds temporal context to session-level observations — Claude now writes "energy dropping after clamshells and squats" instead of just "energy dropping."

Verified with 5 live Claude scenarios: set-specific pain (PASS), general complaint (PASS after prompt fix), exercise-level observation (PASS), no-context (PASS), mid-session energy check-in with temporal context (PASS). Live test script at `backend/scripts/test_observation_attachment_live.py`.

- [x] Parser: tool schema + dataclass + build function + prompt rules 19/22/23
- [x] Validation: dataclass + validate_observation_card with context_entry_count + range/orphan/no-context checks
- [x] Voice: persistence pass-through + context dict includes attached_to_set
- [x] Transcription: RIR keyterms added
- [x] 19 new tests (8 parser, 9 validation, 4 voice pipeline integration) — audit added 2 more edge case tests
- [x] Full audit: audit agent + staff engineer review, 2 edge case tests added from findings

**Result:** 683 total tests (664 existing + 19 new), all green.

#### Day 7: Live Accuracy Testing + Phase Close-Out ✅ COMPLETE

**Mode:** Independent + audit.

Consolidated all live test scenarios into `backend/scripts/test_pipeline_live.py` — single runner with automated scoring against exit criteria. 25 total scenarios across 4 sections: 9 real trainer quotes (Section A), 6 synthetic patterns (Section B), 5 observation attachment tests (Section C), 5 adversarial edge cases (Section D). Adversarial cases: ambiguous exercise reference → yellow flag, noise-only transcript, contradictory correction, long multi-content clip, unknown exercise name. All exit criteria met on first run — no prompt tuning needed. Audit agent re-read all Phase 1b files, found 2 minor quality issues (type hint gap, docstring), both fixed. 683 tests still green.

**Result:** 25/25 live scenarios passing. All exit criteria met. Phase 1b complete.

### Decisions Pending Real-Data Validation

These are heuristic/judgment calls that are reasonable but can only be confirmed with real trainer audio. When something in the pipeline isn't working, check these first.

| Decision | Where | What we assumed | How we'd know it's wrong | What to do |
|----------|-------|-----------------|--------------------------|------------|
| Keyterm priority order | `transcription.py:build_keyterm_list()` | Gym jargon > abbreviations > multi-word names is the right priority for 100 Deepgram keyterm slots | Deepgram consistently mangles a multi-word exercise name that got bumped off the list by a low-value abbreviation | Re-order priorities or add frequency weighting based on which exercises trainers actually say most |
| Skip terms list | `transcription.py:_SKIP_TERMS` | Common single words (squat, bench, curl, fly, etc.) don't need keyterm help | Deepgram misrecognizes one of these words in context (e.g., "fly" → "fry") | Remove from skip list, give it a keyterm slot |
| Abbreviation detection | `transcription.py:_is_abbreviation()` | All-caps + ≤6 chars catches all abbreviations worth prompting | A trainer uses an abbreviation that's lowercase or >6 chars and Deepgram misses it | Expand the heuristic or add explicit aliases to the exercise DB |
| Gym jargon list | `transcription.py:GYM_TERMS` | 19 hardcoded terms (RPE, AMRAP, superset, etc.) are the most important gym vocabulary | A trainer regularly uses a jargon term we missed (e.g., "myo-reps", "cluster set") and Deepgram mangles it | Add to GYM_TERMS list |

**Upcoming (Days 2-7) — add to this table as we build:**

| Decision | Day | What to watch for |
|----------|-----|-------------------|
| Claude parser prompt wording | Day 2-3 | How we instruct Claude to parse transcripts. The biggest heuristic in the project. Tuned on Day 6 with real transcripts. |
| Intent classification logic | Day 3 | How Claude decides "new exercise" vs "additive info" vs "correction" vs "observation." Could be fragile with ambiguous speech. |
| Fuzzy match threshold | Day 4 | What similarity score cutoff we use for exercise name matching. Too low = false matches, too high = misses. |
| Weight unit detection | Day 4 | How we decide if a bare number like "80" means kg or lbs. Context-dependent heuristic. |
| Exercise alias coverage | Ongoing | Trainers might use phrases not in our 3,466 aliases. Only real usage reveals gaps. Extra aliases don't hurt — missing ones do. |

**When to check this table:** After Day 6 (real transcript testing), and whenever the pipeline produces unexpected results.

### Key Concepts

- **Deepgram = ears, Claude = brain.** Deepgram transcribes sound to text. Claude understands and structures it. Our intelligence is in the Claude layer (prompt design, tool schema).
- **Keyterm prompting:** Cheat sheet of 100 gym terms sent to Deepgram to improve recognition of specialized vocabulary. API limit is 100 terms.
- **Tool use:** Instead of Claude writing text, we define a structured schema (matching our DB model) and Claude fills it in like a form. Guaranteed valid JSON.
- **Stateless server:** Phone keeps full session state, sends it with every clip. Server processes each clip in isolation. Handles offline, manual edits, crash recovery, and race conditions.

### Success Criteria

- [x] ≥85% of test transcripts parsed correctly — 100% (25/25)
- [x] ≥90% exercise names normalized to canonical — 100% (25/25)
- [x] ≥95% set/reps extracted correctly — 100% (25/25)
- [x] ≥90% weights extracted correctly — 100% (25/25)
- [x] Additive parsing works on all correction test cases — 100%
- [x] Response time ≤5s per parser call (avg 2.9s) — 96% (24/25)
- [x] 683 total unit/integration tests all passing
- [x] End-of-phase audit completed (audit agent + staff engineer review)

### Pranav's Prep (Before Day 6)

Write 5-10 sample transcripts of real trainer speech. Raw, natural, not polished. Examples of what a trainer actually says mid-session.

---

## Historical Record

### What Was Built in v1

- Git repo initialized, pushed to github.com/pranavjain20/supertrainer (private)
- Docker Compose: Postgres 16 (port 5434) + test DB (port 5433)
- FastAPI app with async SQLAlchemy engine
- 7 SQLAlchemy models, Alembic configured, initial migration
- Seed script, 15 CRUD endpoints, error handling + request logging middleware
- 93 tests passing

### Documentation Phase (Complete)

- [x] TECH_STACK.md — rewritten
- [x] BUILD_PLAN.md — rewritten
- [x] CLAUDE.md — rewritten (pre-work fix applied)
- [x] WORKFLOW.md — updated
- [x] STATUS.md — reset
- [x] tasks/todo.md — rewritten
- [x] Old files moved to reference/

## API Keys Status

- Deepgram: has key
- Anthropic: has key
- Railway: has key
- Supabase: not yet (needed Phase 4)

## Infrastructure

- Docker Compose: Postgres 16 on port 5434, test DB on port 5433
- Python venv at `backend/.venv/`
- Git identity: pranavjain20 / janpranavjain12@gmail.com
