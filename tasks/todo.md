# SuperTrainer — Task Tracker

## Phase 2: Mobile App

### Pre-Work: Backend Addition ✅ COMPLETE
- [x] `GET /api/v1/sessions` — trainer-level session listing with date filter
- [x] `list_sessions_by_trainer()` service function
- [x] 8 new tests (all-sessions, date filter scheduled_for, date filter started_at, no results, no filter, pagination, cross-trainer exclusion, ordering)
- [x] 691 total backend tests passing

### Day 1: Project Setup + Tab Navigation ✅ COMPLETE
- [x] Create Expo project (SDK 54)
- [x] Install dependencies: TanStack Query, Zustand, expo-av, expo-haptics
- [x] NativeWind v4 setup (tailwind.config, metro.config, babel.config, global.css)
- [x] Four-tab navigation: Home, Clients, Brain, Session
- [x] Clients + Session tabs have stack layouts for nested navigation
- [x] Root layout with QueryClientProvider, splash screen, font loading
- [x] Color palette (`src/constants/colors.ts`) + API config (`src/constants/config.ts`)
- [x] App runs on physical phone via Expo Go
- [x] Fast Refresh verified
- [x] Concepts doc: `concepts/phase-2-day-1.md`

### Day 2: API Client + TypeScript Types ✅ COMPLETE
- [x] `src/api/types.ts` — All TypeScript interfaces mirroring backend schemas (enums, generic wrappers, all 10 models, create/update variants, SetData union type)
- [x] `src/api/client.ts` — Fetch wrapper (apiGet/apiPost/apiPatch/apiDelete/apiUpload) with custom ApiError class
- [x] `src/api/clients.ts`, `sessions.ts`, `entries.ts`, `plans.ts`, `voice.ts` — endpoint functions for all CRUD operations
- [x] `src/constants/config.ts` — API_BASE_URL with dev IP (192.168.1.160:8000)

### Day 3: Home Screen + Client List ✅ COMPLETE
- [x] `src/hooks/useClients.ts` — useClients (sorted A-Z, 200 limit) + useClientMap (O(1) lookups)
- [x] `src/hooks/useSessions.ts` — useTodaySessions with client enrichment (joins client names onto sessions)
- [x] Home screen: today's sessions with time/status/duration, pull-to-refresh, empty state ("Enjoy your rest day!")
- [x] Clients screen: search (real-time, case-insensitive), alphabetical grouping by first letter, active count, pull-to-refresh
- [x] Components: ClientRow (initials avatar + deterministic color), SessionRow (status badge), EmptyState, LoadingState, ErrorState
- [x] `src/utils/dates.ts` — formatTime, formatDayHeader, formatMemberSince, toISODateString
- [x] `src/utils/initials.ts` — deterministic initials + color hash from name
- [x] `src/constants/styles.ts` — shared cardShadow

### Day 4: Client Profile ✅ COMPLETE
- [x] `app/(tabs)/clients/[id].tsx` — Client profile screen (491 lines)
- [x] Header: initials avatar, name, "Training since" date
- [x] Three-tab layout: Overview (goals pills + injury history), Sessions (expandable cards with entries), Plans (numbered plan text)
- [x] `src/hooks/useClient.ts` — useClient, useClientSessions (2min stale), useClientPlans
- [x] Expandable session cards: on-demand entry loading via TanStack Query, cached by session ID
- [x] ExerciseCard: set table with reps/weight/RPE/notes, handles both seed and voice pipeline data formats
- [x] ObservationCard: colored left border by flag_color, flag reason header
- [x] Dynamic route navigation from client list

### Day 5: Session Screen + Record Button ✅ COMPLETE
- [x] `useSession.ts` — single session query hook (60s stale)
- [x] `useVoiceRecorder.ts` — expo-av recording lifecycle (permission → record → stop → URI)
- [x] `recordingStore.ts` — Zustand store for cross-component recording state
- [x] `RecordButton.tsx` — animated button (80px, 1.25x recording scale, pulse ring, haptics)
- [x] `[sessionId].tsx` — recording screen (header, empty timeline, bottom record bar)
- [x] `session/index.tsx` — replaced placeholder with session list
- [x] `session/_layout.tsx` — registered [sessionId] route
- [x] `(tabs)/index.tsx` — wired home screen session navigation
- [x] `(tabs)/_layout.tsx` — recording navigation guards on all tabs
- [x] Audit: disabled button for completed sessions, fixed useCallback deps

### Days 6-7: Voice Pipeline + Inline Editing ✅ COMPLETE
- [x] Voice clip upload pipeline (sessionStore, useVoiceClipUpload, Timeline)
- [x] Tap-to-edit modals (ExerciseEditModal, ObservationEditModal)
- [x] Optimistic cache updates via setQueryData
- [x] useEditableEntries shared hook
- [x] 694 backend tests passing

### Day 8: Cross-Tab Navigation + Session Flow Polish ✅ COMPLETE
- [x] Recording screen at root level (above tabs)
- [x] Swipe-back guard during recording
- [x] Session list UX (status pills, continue button, countdown)
- [x] Custom back buttons, ConfirmSheet, timeline scroll fix

### Day 9: End Session Flow + UX Polish ✅ COMPLETE
- [x] Server-side duration computation
- [x] Summary card + Workout Details + Done button
- [x] Client profile session summaries with workout type
- [x] Dead code cleanup, typography hierarchy
- [x] 725 backend tests passing

### Day 10: Golden Audit (Days 6-10) — Pending Phone Testing
- [x] BUG: Remove ended session filter in useSessions.ts
- [x] TYPE SAFETY: Add null to SessionEntryUpdate, remove unsafe cast
- [x] DRY: Extract numberExercises utility (3 call sites)
- [x] DRY: Extract SessionHeader component
- [x] TEST GAP: Threshold boundary tests for workout classifier
- [x] Dependency fix: lines-and-columns added to package.json
- [x] 727 backend tests passing
- [x] Phone testing checklist (10 core flows + 5 edge cases) — Day 11, all passed
- [x] Fix anything that fails — 12 UX fixes applied live

### Day 12: Final UX + Merge

- [ ] **"Didn't catch that" UX for failed voice clips**
  The problem: When the AI parser can't understand a voice clip (mumbled speech, too much background noise, ambiguous reference), it currently creates a yellow-flagged observation card in the timeline. This is wrong because:
  1. The trainer is mid-session coaching a client — they glance at their phone and see a yellow card with text like "Unclear reference — could not determine which exercise was mentioned." They don't know what that means. Their brain is on their client, not on debugging AI output.
  2. It looks identical to a real observation (e.g., "Knee pain reported"). The trainer can't instantly tell the difference between "something about my client" and "the system didn't understand me."
  3. Yellow observation cards have meaning — they're "something to watch" flags (fatigue, minor discomfort). Using the same visual for "I didn't understand" dilutes that meaning.

  What it should be instead: A visually distinct "system message" card in the timeline — clearly not a client observation. Something like a muted/grey card with an icon and simple text: "Couldn't understand that clip" with a "Tap to retry" or "Tap to type it manually" action. The trainer should instantly know: (a) this is the app talking to me, not a note about my client, and (b) I need to re-record or type it.

  Backend context: The parser already handles this correctly — Rule 8 in `parser.py` creates a yellow observation card for ambiguous/unclear input. The voice endpoint (`api/voice.py`) separates these into `clarifications_needed` (not persisted as entries). The fix is frontend: instead of rendering clarifications as observation cards, render them as a distinct "system message" component in the timeline.

  Files to look at: `mobile/src/hooks/useVoiceClipUpload.ts` (where clarifications come back from the API), `mobile/src/components/Timeline.tsx` (where cards render), `mobile/src/components/ObservationCard.tsx` (current yellow card), `backend/app/api/voice.py` (clarifications_needed response field).

- [ ] **Active session banner — always-visible return path**
  The problem: When a trainer is mid-session recording and navigates away (taps back, checks another client, goes to Home), there's no obvious way to get back to the active session. The back button takes them to wherever they came from (e.g., client profile), not back to the session. The only way back is to go to the Home tab and tap "Continue Session" — but the trainer doesn't know that. They're confused and disoriented mid-session.

  What it should be: A persistent banner visible on every screen when there's an active (in-progress) session. Something like a small bar: "Recording with Jake Morrison · 12:34" that taps to return to the recording screen. Similar to how Uber shows your active ride across all screens, or how phone apps show an active call banner. The trainer should never lose track of their active session regardless of where they navigate.

  Implementation notes: This lives in the root layout (`app/_layout.tsx` or `app/(tabs)/_layout.tsx`), needs to read from a global store (Zustand — possibly extend `recordingStore.ts` or `sessionStore.ts`) to know if there's an active session, and renders above/below the tab bar. The banner should show client name, elapsed time, and navigate to `recording/[sessionId]` on tap. It should disappear when the session is ended.

  Files to look at: `mobile/app/_layout.tsx` (root layout), `mobile/app/(tabs)/_layout.tsx` (tab layout where banner would render), `mobile/src/stores/sessionStore.ts` (active session state), `mobile/src/stores/recordingStore.ts` (recording state), `mobile/app/recording/[sessionId].tsx` (recording screen to navigate to).

- [ ] **Phone test items 2 and 3** on device
- [ ] **Merge `feat/phase-2a-mobile` to master** — Phase 2a COMPLETE

### Post-Merge: Planning Discussion

- [ ] **Planning discussion:** Define the minimum feature set a trainer needs to actually use this app, where every piece is production-grade. Decide what to build next — brain first (for credibility/wow factor) or production polish first (auth, onboarding, client creation) so a real trainer can use it. Key principle: whatever ships must be flawless, even if not everything ships yet.

---

## Phase 1b: Voice Pipeline — COMPLETE (683 tests)

<details>
<summary>Phase 1b completed tasks (click to expand)</summary>

## Phase 1b: Voice Pipeline (Week 3-4)

### Day 1: Exercise Database + Deepgram Service ✅ COMPLETE
- [x] Expand exercises from 19 → 142 (3,466 aliases, specific anatomy, expert common_errors)
- [x] Select top 100 keyterms for Deepgram prompting (priority algorithm: gym jargon > abbreviations > multi-word)
- [x] Create `services/transcription.py` — Deepgram STT integration (async, error handling)
- [x] Add `deepgram-sdk` to requirements.txt
- [x] Unit tests: Deepgram service with mocked API responses (24 tests)
- [x] Comprehensive exercise DB test suite — comparative metrics, trainer speech recognition, structural quality, keyterm coverage (36 tests)
- [x] Document heuristic decisions pending real-data validation in STATUS.md
- [x] 366 total tests passing

### Day 2: Claude Parser — Tool Schema + Core Parsing ✅ COMPLETE
- [x] Design tool_use schema matching SessionEntry model (exercise_card + observation_card tools)
- [x] Write system prompt for parser (10 rules)
- [x] Create `services/parser.py` — Claude transcript → structured data via tool_use
- [x] Core parsing: single exercises, basic set/rep/weight extraction
- [x] Add `anthropic` to requirements.txt
- [x] Unit tests: parser with mocked Claude responses (30 tests)
- [x] Created `concepts/2026-02-24.md` — tool_use learning document
- [x] 396 total tests passing

### Day 3: Parser — Intent Classification + Additive Parsing + Context ✅ COMPLETE
- [x] Session context formatting: `format_session_context()` with numbered entry IDs
- [x] `parse_transcript()` accepts `session_context` parameter (backward compatible)
- [x] `modify_exercise_card` tool schema (target_entry_id, action, target_sets, updates)
- [x] `ParsedModification` dataclass + wiring in `_extract_parser_result()`
- [x] System prompt rules 11-15 (intent routing, ambiguity handling, conservative correction)
- [x] Integration tests: intent classification, edge cases, backward compatibility
- [x] 433 total tests passing (37 new)

### Day 4: Validation Layer ✅ COMPLETE
- [x] Create `services/validation.py` — fuzzy match exercise names to canonical DB (rapidfuzz)
- [x] Weight normalization: "185 pounds" → 83.9 kg, "80 kilos" → 80.0 kg
- [x] **Per-client weight unit default:** `preferred_weight_unit` column on Client (Literal["kg", "lbs"], default "kg"), migration, 4 client tests
- [x] ~~Set expansion: "3 sets of 10 at 80" → 3 individual set records~~ *(handled by parser, not validation)*
- [x] Pain extraction: detect pain/injury mentions, map body parts, extract severity
- [x] Validation hardening: word-boundary regex, 30 new pain keywords, 33 new body parts, 10 severity modifiers, negation handling, comma clause splitting, suspicious value warnings
- [x] Add `rapidfuzz` to requirements.txt
- [x] Tests: 115 validation tests + 4 client tests, 552 total passing

### Day 5: Voice Clip Endpoint + Integration Tests ✅ COMPLETE
- [x] Create `api/voice.py` — `POST /api/v1/sessions/{session_id}/voice-clip`
- [x] Wire Deepgram → parser → validation pipeline via `services/voice.py`
- [x] Return structured entry + timing breakdown (transcription_ms, parsing_ms, validation_ms, persistence_ms)
- [x] **Clarification handling:** Yellow-flagged observations returned as `clarifications_needed` (not persisted as entries)
- [x] Register voice router in main.py
- [x] Integration tests: 15 pipeline tests with mocked Deepgram + Claude
- [x] Test hardening: 27 additional tests (helpers, weight units, modification edge cases, mixed content, data integrity)
- [x] 594 total tests passing

### Day 6: Set-Level Observation Attachment + Temporal Context ✅ COMPLETE
- [x] Set-level observation attachment (target_entry_id + attached_to_set through parser → validation → persistence)
- [x] Prompt rules 19/22/23 — during-exercise vs between-exercise distinction, temporal context
- [x] 5 live Claude scenarios passing (set-specific pain, general complaint, exercise-level, no-context, temporal)
- [x] 19 new tests (8 parser, 9 validation, 4 voice pipeline integration) + 2 audit edge cases
- [x] 683 total tests passing

### Day 7: Live Accuracy Testing + Phase Close-Out ✅ COMPLETE
- [x] Consolidated live test runner (`backend/scripts/test_pipeline_live.py`) — 25 scenarios, automated scoring
- [x] 9 real trainer quotes, 6 synthetic patterns, 5 observation attachment, 5 adversarial edge cases
- [x] All 25/25 scenarios passing on first run — no prompt tuning needed
- [x] Full audit: audit agent + staff engineer review, 2 minor quality issues fixed
- [x] 683 total tests green, all exit criteria met

### Exit Criteria ✅ ALL MET
- [x] ≥85% of test transcripts parsed correctly — **100% (25/25)**
- [x] ≥90% exercise names normalized to canonical — **100%**
- [x] ≥95% set/reps extracted correctly — **100%**
- [x] ≥90% weights extracted correctly — **100%**
- [x] Additive parsing works on all correction test cases — **100%**
- [x] Response time ≤5s per parser call (avg 2.9s) — **96% (24/25)**
- [x] 683 total tests, all green
- [x] End-of-phase audit completed

</details>

---

## Phase 1a: Backend Foundation — COMPLETE (306 tests)

<details>
<summary>Phase 1a completed tasks (click to expand)</summary>

### Models + Database
- [x] New models.py with 10 models (trainers, clients, sessions, session_entries, session_plans, injury_flags, client_analysis, exercises, brain_conversations, brain_messages)
- [x] New schemas.py for all request/response types (34 classes, 65 tests)
- [x] Delete old Alembic migrations
- [x] Enable pgvector extension + embedding columns for text-heavy fields
- [x] Fresh Alembic migration for new schema
- [x] Verify all models create and query correctly (22 tests)

### CRUD Endpoints
- [x] Client CRUD: list (cursor pagination, archive filter), create, get, update, archive + tests (25 tests)
- [x] Session CRUD: create (with scheduled_for, plan_id), get, list by client, update, delete + tests (25 tests)
- [x] Fix main.py (remove exercise_logs_router, unblock app startup)
- [x] Fix injury_flags.py (exercise_log_id → session_entry_id validation)
- [x] Add plan_id FK validation to session create
- [x] HTTP test fixtures in conftest.py (client, trainer_for_api, trainer_and_client)
- [x] Session entry CRUD: create (exercise_card + observation_card types), list by session, list by client, get, update, delete + tests (55 tests)
- [x] Session plan CRUD: create, get by client, update, delete + tests (28 tests)
- [x] Injury flag CRUD: create, list, get, update, delete + tests (37 tests)
- [x] Verify error handling middleware works with new endpoints (4 tests)

### Day 5 Golden Audit Fixes
- [x] Extract shared dependencies.py (get_trainer_id, validate_client_ownership, validate_session_ownership)
- [x] Add ownership validation to clients.py (get, update, archive, list_sessions)
- [x] Add ownership validation to sessions.py (create, get, update, delete) + plan_id ownership
- [x] Fix SessionPlan.trainer_id FK missing ondelete="CASCADE"
- [x] Add cross-field validator to SessionEntryUpdate schema
- [x] Add attached_to_set validation for exercise_cards
- [x] Add min_length=1 to exercise_canonical
- [x] Rename injury_flag_service functions to match naming convention
- [x] Add cross-trainer ownership tests for clients (5 tests)
- [x] Add cross-trainer ownership tests for sessions (6 tests)
- [x] Add cross-trainer ownership test for entries list_by_client (1 test)
- [x] Add schema validation tests for new validators (8 tests)
- [x] Second audit pass — caught plan_id ownership gap, fixed + tested
- [x] 262 tests passing

### Seed Data
- [x] New seed.py: 5 clients with 1/3/5/10/15 sessions
- [x] Seed session_plans for clients with 5+ sessions
- [x] Seed injury_flags with varied body parts and pain levels
- [x] Seed 19 canonical exercises in Exercise table
- [x] 10 seed tests (counts, relationships, idempotency)

### Days 8-10: Audit + Polish + Merge
- [x] Fix 3 missing ondelete="CASCADE" on trainer FK columns
- [x] Consolidate ownership validators into dependencies.py
- [x] Replace response_model=dict with DataResponse[XResponse] on all endpoints
- [x] End-of-phase audit: cross-type contamination fix, resolved_at validation
- [x] Day 10 golden audit: pagination helper extraction, alembic env fix
- [x] Squash merge to master — 306 tests passing

</details>
