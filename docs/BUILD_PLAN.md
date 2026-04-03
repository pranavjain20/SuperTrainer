# SuperTrainer: Build Plan (PRD v3)

---

## v1 Scope (Finalized Apr 3, 2026)

**v1 target:** Replace the trainer's notebook. Must be simpler, cleaner, and faster than GoodNotes on iPad, physical notebooks, Notes app, or relying on memory.

### Tier 1 — Notebook Replacement (must ship)

| # | Item | Status | What it means | Depends on |
|---|------|--------|--------------|------------|
| 1 | Compact exercise format | Logic done, visual unreviewed | "4kg x10, 3kg x8" one-liner. How trainers actually write. Prerequisite for display. | — |
| 2 | Live exercise history | Scoped, not built | See what client did last time for each exercise. #1 daily action (8-15x/session). Faster than GoodNotes. | #1 |
| 3 | Plan creation from app | Backend exists, no mobile UI | Create plans via voice or text. | — |
| 4 | Plan modification on the fly | Backend exists, no mobile UI | Modify plan mid-session when things change. | #3 |
| 5 | End-session plan dictation | Not built | "Anything for next time?" -> saves as plan. | #3 |
| 6 | Settings (weight units) | Not built | US trainers need lbs. No settings screen exists. | — |

### Tier 2 — Intelligence Layer (ships with v1)

| # | Item | Status | What it means | Depends on |
|---|------|--------|--------------|------------|
| 7 | Session summaries | Not built | 2-3 sentence AI recap per session. | — |
| 8 | Flag system (AI auto-assign) | Partial — display only | AI assigns flags on session save. Trainer can override. | — |
| 9 | Pre-session briefing | Not built | 4-layer AI summary before each client arrives. | #7, #8 |

### Conditional

| # | Item | Status | Decision |
|---|------|--------|----------|
| 10 | Session detail view | Not built | Decide after #1 visual review — pull in if expandable cards feel cramped. |

### Deferred to post-v1

| Item | Original Phase | Why deferred |
|------|---------------|-------------|
| The Brain (conversational agent) | Phase 3c | Biggest build. Better with real trainer data. Post-v1 capstone. |
| Pattern detection | Phase 5a | Needs longitudinal data to be meaningful. Feeds into briefings later. |
| Push notifications | Phase 3b | Briefing delivery before sessions. Useful but not blocking daily workflow. |
| Onboarding flow | Phase 2b | Manual setup for single trainer beta. Not needed at scale yet. |
| Auth | Phase 4a | Single user. Not needed until multi-trainer. |
| Swipe navigation | Phase 2b | Browse prev/next session. Convenient, not blocking. |
| Home screen flag indicators | Phase 2b | Red/orange dot on flagged clients. Depends on flag system. |
| Plan vs actual comparison | Phase 3a | Silent tracking of planned vs done. Nice-to-have. |
| Progress charts | Phase 5b | Visual weight/volume trends. Needs longitudinal data. |
| iPad layout | Post-launch | Responsive layouts for 12" screens. UI pass, no logic changes. |

*Note: The original phase timeline below was the initial build plan. Phases 1a, 1b, and 2a are complete. The v1 scope above replaces the Phase 2b-3c ordering — we cherry-picked the highest-impact items across those phases.*

---

## Timeline Overview (Original)

Every phase is ≤2 weeks. Review and approve each before moving to the next.

| Phase | Weeks | What |
|-------|-------|------|
| **1a** | 1-2 | Backend Foundation (models, CRUD, seed data) |
| **1b** | 3-4 | Voice Pipeline (Deepgram + Claude parser) |
| **2a** | 5-6 | Mobile — Core Session Screen + Navigation |
| **2b** | 7 | Mobile — Session Detail + Flags + Onboarding |
| **3a** | 8-9 | Planning Flow (voice → structured plans) |
| **3b** | 10 | Pre-Session Briefing (4-layer, push notifications) |
| **3c** | 11-12 | The Brain (RAG, honest states, plan actions) |
| **4a** | 13-14 | Calendar Integration + Auth |
| **4b** | 15-16 | Polish + Beta Launch |
| **5a** | 17-18 | Client Score + Pattern Detection |
| **5b** | 19-20 | Injury Risk Scoring + Progress Charts |
| **6a** | 21-22 | Client App + Wearable Integration |
| **6b** | 23-24 | Multi-Trainer + Session Sharing + Scale |

Total: ~6 months part-time (3-4 hrs/day from Pranav, unlimited from Claude Code agents)

---

## How We Work Together

**Pranav's role (3-4 hrs/day):**
- Review code (most important — you must understand everything)
- Make product decisions when I hit forks
- Test on your physical phone
- Write/refine sample transcripts (you know what trainers say, I don't)
- Approve or reject architectural choices

**My role (Claude Code, up to 4 parallel agents):**
- Write code, tests, and iterate
- Prepare multiple features in parallel while you sleep/study
- When you come online, you review what's ready
- I never merge anything you haven't reviewed

**Daily rhythm:**
1. You open terminal, I tell you what's ready for review
2. You review, give feedback, make decisions
3. I implement feedback + continue building next items
4. You test on phone, report issues
5. I fix issues, prepare tomorrow's batch

---

## Feature Dependency Map

```
Models + Database (10 models)
    ↓
    ├── Client CRUD
    ├── Session CRUD (with scheduled_for)
    ├── Session Entry CRUD (exercise_card + observation_card)
    ├── Session Plan CRUD
    └── Injury Flag CRUD
            ↓
            └── Voice Pipeline (Deepgram + Claude Parser)
                    ├── Per-clip synchronous processing
                    ├── Session state management (client-side)
                    └── Intent classification + additive parsing
                            ↓
                            ├── Mobile — Core Session Flow
                            │       ├── Navigation shell
                            │       ├── Tap-to-speak + real-time timeline
                            │       ├── Client profile + session history
                            │       └── Onboarding
                            │
                            ├── Planning Flow (voice → exercise cards)
                            │       ↓
                            │       └── Pre-Session Briefing (4-layer)
                            │               └── Push notifications
                            │
                            └── The Brain (RAG + agent)
                                    ├── Single + cross-client queries
                                    ├── Three honest states
                                    ├── Plan actions via voice
                                    └── Conversation history

Auth (Supabase) — added as middleware in Phase 4a
Calendar — added in Phase 4a
Intelligence Layer — Phase 5 (patterns, scoring, charts)
```

**What can be parallelized:**
- Backend CRUD endpoints (clients, sessions, entries, plans, injuries — all independent)
- Backend CRUD + Mobile scaffolding (different agents, same phase)
- Voice pipeline services (Deepgram + Claude parser + exercise DB — independent)
- Pattern detection algorithms (weight, pain, form, volume — independent)
- Brain service + Briefing service (both need data, independent of each other)

---

## Phase 1a: Backend Foundation (Weeks 1-2)

**Goal:** New database schema, all CRUD endpoints working, rich seed data.

**What gets built:**
- All 10 SQLAlchemy models: trainers, clients, sessions, session_entries, session_plans, injury_flags, client_analysis, exercises, brain_conversations, brain_messages
- pgvector extension enabled + embedding columns for text-heavy fields (observation_text, form_notes, plan_text, raw_transcript)
- Pydantic schemas for all request/response types
- Delete old Alembic migrations, fresh migration for new schema
- Seed script: 5 synthetic clients with 1/3/5/10/15 sessions each
- Client CRUD: list (cursor pagination, archive filter), create, get, update, archive
- Session CRUD: create (with scheduled_for), get, list by client, update, delete
- Session entry CRUD: create (exercise_card + observation_card types), list by session, list by client
- Session plan CRUD: create, get by client, update
- Injury flag CRUD: create, list by client
- Standard response format + error handling middleware + request logging
- Pagination (cursor-based)

**Agent parallelization:**
- Agent 1: Models + database setup + migrations
- Agent 2: Pydantic schemas + seed script
- Agent 3: Client + session endpoints + tests
- Agent 4: Session entry + plan + injury flag endpoints + tests

**Pranav's time:**
- Review data model (10 models, compare against PRD v3) (~1 hr)
- Review seed data profiles (~30 min)
- Review and approve all code (~2 hrs)

**Testing plan:**
- All models create and query correctly
- All Pydantic schemas validate (valid + invalid inputs)
- Database constraints enforced (unique, FK integrity, check constraints)
- JSONB fields serialize/deserialize (sets data, cue_effectiveness, score_breakdown)
- Each endpoint: correct status codes (200, 201, 404, 422)
- List endpoints paginate correctly (cursor-based, no page overlap)
- Create endpoints validate required fields
- Update endpoints handle partial updates (PATCH)
- Archive client doesn't delete data (soft delete)
- entry_type validation (must be exercise_card or observation_card)
- Cross-entity ownership validated (session belongs to client, entry belongs to session)
- Cascade deletes verified (session delete cascades to entries)
- Error responses match standard format `{"error": {...}}`
- Invalid UUIDs return 404 not 500
- Empty database returns empty lists, not errors
- Seed script populates correctly
- Total tests: ~60-80

**Milestone:** All CRUD tests pass, API serves seeded synthetic data, Swagger docs show all endpoints.

---

## Phase 1b: Voice Pipeline (Weeks 3-4)

**Goal:** Per-clip voice processing. Trainer speaks -> structured session entry in <=3 seconds.

**What gets built:**
- Deepgram service: per-clip audio -> transcript (with keyterm prompting for exercise names)
- Claude parser service: transcript + full session context -> structured JSON (via tool_use)
- Session state management: client maintains full session state, sends with each clip request. Server is stateless.
- Intent classification: new exercise, additive (updating previous entry), set-level note, exercise-level note, observation card
- Additive parsing: "oh, 80 kilos I forgot" correctly updates previous exercise entry
- Rule-based validation layer:
  - Exercise name normalization (fuzzy match to canonical database)
  - Weight unit detection and normalization (always stored as kg)
  - Implicit set expansion ("3 sets of 10" -> 3 individual set records)
  - Pain report extraction with body part mapping
- Exercise database: seed 100 common exercises + aliases
- Audio upload endpoint (Supabase Storage)
- Real-time voice clip endpoint: POST /sessions/{id}/voice-clip -> parsed entry in <=3 seconds
- Embedding generation on session save (for pgvector, used by Brain in Phase 3c)
- Parser test suite: 15+ transcript samples covering all intent types

**Agent parallelization:**
- Agent 1: Deepgram integration service + tests
- Agent 2: Claude parser service + prompt engineering
- Agent 3: Validation layer (exercise matching, weight normalization, set expansion)
- Agent 4: Exercise database + voice clip endpoint + integration tests

**Pranav's time (critical):**
- Write 5-10 sample transcripts of what a trainer actually says (~2 hrs)
- Review parser output and give feedback (~1 hr)
- Iterate on prompt (~1 hr)

**Testing plan:**
- Deepgram returns transcript for clean audio
- Deepgram returns transcript for noisy audio
- Deepgram keyterm prompting improves exercise name recognition
- Claude parser extracts exercises from simple transcript
- Claude parser extracts multiple exercises from one transcript
- Claude parser handles additive parsing ("oh, 80 kilos")
- Claude parser classifies intent correctly (exercise card vs observation card)
- Claude parser maintains session state across clips (knows current exercise/set)
- Claude parser extracts form observations, pain reports, coaching cues
- Claude parser handles implicit sets ("3 more sets at 145")
- Claude parser handles weight changes ("dropped to 135")
- Claude parser handles RPE mentions
- Validation normalizes exercise names (fuzzy match)
- Validation converts weight units to kg
- Validation handles ambiguous exercise names (flags for review)
- End-to-end: voice clip + session context -> structured entry in <=3 seconds
- Parser gracefully handles garbage/empty transcript
- Parser handles transcript with no exercises (creates observation card)
- Total tests: ~30-40

**Milestone:** Speak naturally -> correctly parsed exercise card or observation card at 85%+ accuracy within 3 seconds.

**CRITICAL CHECKPOINT:** Does per-clip parsing work at 85%+ accuracy? If not, fix before moving to Phase 2a. Everything downstream depends on this.

---

## Phase 2a: Mobile — Core Session Screen + Navigation (Weeks 5-6)

**Goal:** Full navigation shell, session recording with real-time timeline.

**What gets built:**
- React Native + Expo project setup
- Bottom navigation: Home, Clients, Brain (placeholder), Session (contextual)
- Trainer home screen: calendar-style today's sessions list
  - Each row: session time + client name
  - Two entry points: tap row -> client profile, "Today's Plan" button -> plan view
  - Empty state: "No sessions today"
- Clients screen: alphabetical list, search bar, date-added sort
- Client profile screen: identity/goals, status indicator (placeholder), next session, session history list
- Session screen with real-time timeline:
  - Exercise cards (structured: exercise name, sets, reps, weight)
  - Observation cards (freeform: observations, pain, coaching notes)
  - Cards build live as trainer speaks
- Tap-to-speak button: visually expands when active, contracts when stopped, haptic on both taps
- Inline editing on all timeline fields (exercise name, weight, reps, notes)
- End session flow: review summary -> "Anything to note for next time?" -> save plan dictation -> confirm -> save
- API client layer with error handling
- TypeScript types matching backend Pydantic schemas

**Agent parallelization:**
- Agent 1: Expo project setup + navigation structure
- Agent 2: API client service + TypeScript types
- Agent 3: Home screen + Clients screen + Client profile
- Agent 4: Session screen + tap-to-speak + timeline components

**Testing plan:**
- App launches without crash
- Navigation between all tabs works
- Client list loads and displays all clients
- Client profile shows correct data
- Session screen: tap to record -> clip sent to API -> parsed entry appears on timeline
- Exercise card renders correctly (name, sets, reps, weight)
- Observation card renders correctly (freeform text)
- Inline editing updates fields
- End session flow saves to backend
- Plan dictation saves to session_plans
- Home screen shows today's sessions
- Empty states display correctly
- Loading and error states work
- Total tests: ~20-25

**Milestone:** Full navigation working, tap to record -> see live timeline -> save session end-to-end.

---

## Phase 2b: Mobile — Session Detail + Flags + Onboarding (Week 7)

**Goal:** Session history browsing, flag system, onboarding.

**What gets built:**
- Session detail view: AI one-line summary at top, full timeline below
- Swipe navigation between sessions (previous/next for same client)
- Flag system:
  - AI assigns flags on session save (green/yellow/orange/red based on content)
  - Flags visible on session rows in client history
  - Flags visible inside session detail on specific entries
  - Trainer can override any flag (tap to change)
- Client profile: session history list with flags visible
- Onboarding flow: trainer profile setup -> guided first client creation
- Home screen: small indicator on client row if recent red/orange flag

**Agent parallelization:**
- Agent 1: Session detail view + swipe navigation
- Agent 2: Flag system (AI assignment + display + override)
- Agent 3: Onboarding flow
- Agent 4: Polish + comprehensive test sweep

**Testing plan:**
- Session detail shows AI summary and full timeline
- Swipe between sessions works
- Flags assigned correctly based on session content
- Flags display on session rows
- Trainer can override flags
- Onboarding creates trainer profile and first client
- Total tests: ~15-20

**Milestone:** Complete client profile and session history end to end. Flag system functional.

**MVP CHECKPOINT:** Can you record on your phone, speak naturally, see a live timeline build, save, and browse session history? If yes, core interaction works. If not, diagnose before Phase 3a.

---

## Phase 3a: Planning Flow (Weeks 8-9)

**Goal:** Trainers can create, view, and modify session plans via voice.

**What gets built:**
- Planning flow: voice input -> AI structures into exercise cards (same format as session timeline)
- Plan creation and modification endpoints
- Deep preparation view: today's plan displayed as structured exercise cards
- Plan fields only contain what trainer said — weight/reps optional, never inferred, never zero
- End-session plan dictation: "Anything to note for next time?" saves to session_plans
- Plan vs. actual: plan_id FK on sessions enables comparison (tracked silently, never enforced)
- Plan and session completely independent — plan never invalidated by different session

**Testing plan:**
- Voice dictate a plan -> structured exercise cards created
- Plan fields empty when not specified (no inference, no zero)
- End-session plan dictation saves correctly
- Plan modification (add/remove exercise, update sets/reps) works
- Plan and session independence verified
- Total tests: ~15-20

**Milestone:** Trainer can voice-dictate a plan, see it structured, modify it — completely independent of sessions.

---

## Phase 3b: Pre-Session Briefing (Week 10)

**Goal:** Push notification with adaptive 4-layer briefing before sessions.

**What gets built:**
- Briefing service: 4-layer generation
  - Layer 0: Today's plan (or "No plan set — want to add one?")
  - Layer 1: Last session (any muscle group) — notable observations only
  - Layer 2: Last session of same muscle group — exercise-specific context
  - Layer 3: Trend flags for today's exercises — scored by recency x severity x trend direction x actionability
- Data maturity gates enforced in backend:
  - 0 sessions: no briefing
  - 1 session: Layer 1 only
  - 2-3 sessions: Layer 0 + Layer 1
  - 4+ sessions: all layers active
  - 10+ sessions: richer trend analysis
- Briefing scoring: top 2-3 flags max, hide empty layers entirely
- Briefing endpoint: GET /clients/{id}/briefing
- Push notification 10-15 minutes before session (Expo Push)
- Notification content: client name + one-line preview of most important flag
- Briefing screen in mobile: conditional layer display, no filler text
- Cache briefing, invalidate on new session data
- "No plan set — want to add one?" nudge when plan missing

**Testing plan:**
- Briefing generates correctly for each data maturity level (0/1/2-3/4+/10+ sessions)
- Empty layers hidden entirely
- Briefing scoring ranks flags correctly
- Max 2-3 flags surfaced
- Push notification fires at correct time
- Cache invalidation on new session data
- "No plan set" nudge appears correctly
- Total tests: ~20-25

**Milestone:** Push notification fires, tap opens briefing, 4 layers display correctly based on available data.

---

## Phase 3c: The Brain — Conversational Agent (Weeks 11-12)

**Goal:** Conversational AI that knows everything about every client, takes actions.

**What gets built:**
- Hybrid RAG architecture: structured SQL for precise queries + pgvector semantic search for fuzzy queries
- Brain service: Claude Sonnet with system prompt enforcing three honest states
  - State 1: Full answer (knowledge + client data)
  - State 2: Partial answer (knowledge but insufficient client data — be honest about gaps)
  - State 3: Neither (honest "I don't know" — web search via Tavily added here)
- Single-client queries with session citation
- Cross-client queries (retrieve from all clients, reason across)
- Action-taking V1: create plan, modify plan (add/remove exercise, update sets/reps/weight) via structured tool calls
- Confirmation required before irreversible actions
- Conversation history: threads stored in brain_conversations + brain_messages
- Brain tab in bottom nav: current conversation + conversation history (like Claude.ai)
- Brain accessible mid-session (secondary button, session state preserved)
- Brain opens from briefing with briefing context pre-loaded
- Full unrestricted brain — not scoped to single client even when opened from briefing
- Response time: under 3 seconds single-client, under 5 seconds cross-client

**Testing plan:**
- Brain answers single-client questions accurately (cites specific sessions)
- Brain answers cross-client questions
- Brain correctly identifies which honest state it's in
- Brain never halluccinates client data
- Brain creates plan via voice instruction
- Brain modifies plan (add/remove exercise, update sets/reps/weight)
- Brain asks for confirmation on irreversible actions
- Conversation history stored and retrievable
- Brain accessible mid-session without disrupting session state
- Brain not scoped to single client when opened from briefing
- Response times within targets
- Total tests: ~25-30

**Milestone:** Ask brain anything about any client -> accurate, cited answer. Brain creates/modifies plans via voice.

**BRAIN CHECKPOINT:** Is The Brain genuinely useful? Accurate answers, no hallucination, plan actions work? If yes, move to Phase 4a. If not, iterate.

---

## Phase 4a: Calendar + Auth (Weeks 13-14)

**Goal:** Calendar integration and real authentication. Trainer data is properly scoped.

**What gets built:**

*Week 13 — Calendar:*
- Google Calendar OAuth integration
- Apple Calendar integration
- Session auto-detection from calendar events
- Trainer-to-client contact mapping (one-time setup, automatic thereafter)
- Pre-session notification triggered from calendar events
- Calendar connection settings screen

*Week 14 — Auth:*
- Supabase Auth integration (email signup + Google OAuth)
- JWT handling in mobile app (secure storage)
- Trainer-scoped data access (all queries filter by trainer_id)
- Password reset flow
- Audit logging

**Testing plan:**
- Calendar OAuth flow completes successfully
- Sessions auto-created from calendar events
- Contact-to-client mapping works
- Briefing notification fires from calendar-detected sessions
- Registration creates account
- Login returns valid JWT
- Trainer A cannot see Trainer B's data
- Expired token returns 401
- Password reset works
- Total tests: ~25-30

**Milestone:** Calendar-driven sessions appear in app. Real login works. Data is properly scoped per trainer.

---

## Phase 4b: Polish + Beta Launch (Weeks 15-16)

**Goal:** Production-ready app. Ship to real trainers.

**What gets built:**

*Week 15 — Polish:*
- Settings screen (units kg/lbs, notifications, account, calendar connection)
- Loading states, error handling, edge cases throughout entire app
- Performance optimization (query efficiency, caching, indexes)
- App Store / Play Store build prep (Expo EAS)
- Exercise database expanded to 200+ exercises

*Week 16 — Beta:*
- Bug bash: fix everything found in self-testing
- Parser accuracy review: full test suite, iterate prompt if needed
- Brain accuracy review: test all three honest states on real queries
- Deploy to production
- Onboard 5-10 beta trainers (personal network, gym contacts)
- Monitor: error rates, API costs, edit rate, brain query accuracy, plan adoption rate

**Testing plan:**
- Weight displays in user's preferred unit
- All screens show loading/error/empty states correctly
- API endpoints respond in <200ms (p95) for CRUD
- Briefing generation responds in <3 seconds (p95)
- No crashes after 30 minutes continuous use
- Total tests: ~15-20

**Milestone:** App deployed to production. 5-10 trainers onboarded and using it.

**BETA READINESS CHECKPOINT:** Would you give this app to a trainer friend and not be embarrassed? Parser 85%+, brain doesn't hallucinate, briefings useful, planning works. If yes, launch.

---

## Phase 5a: Client Score + Pattern Detection (Weeks 17-18)

**Goal:** Automated pattern detection and holistic client scoring.

**What gets built:**
- Client score algorithm: progression toward goals + injury risk + consistency -> 0-100 score
- Score stored in client_analysis.client_score with JSONB breakdown for explainability
- Green/yellow/red indicator on client profile
- Data maturity: "Not enough data yet" for clients with <4-6 sessions
- Pattern detection engine:
  - Weight progression rate (too fast / stagnant / healthy)
  - Pain frequency by body part (recurring = flag, threshold-based)
  - Form quality degradation (increasing error rate over sessions)
  - Volume and overtraining indicators
  - Cue effectiveness tracking
- client_analysis recomputed after each session save
- Pattern results surfaced in briefing Layer 3

**Testing plan:**
- Client score calculation is deterministic (same input = same score)
- Score handles clients with <4 sessions ("Not enough data")
- Weight progression detects healthy / stagnant / too-fast
- Pain frequency flags recurring body part issues
- Form quality detects increasing error rate
- Patterns surface correctly in briefing Layer 3
- Total tests: ~20-25

**Milestone:** Client profiles show green/yellow/red indicators. Briefings surface meaningful patterns.

---

## Phase 5b: Injury Risk Scoring + Progress Charts (Weeks 19-20)

**Goal:** Explainable risk scores and visual progress tracking.

**What gets built:**
- Injury risk scoring: rule-based weighted formula (0-100, Low/Medium/High)
- Explainable: shows top risk factors driving the score
- Risk score feeds into overall client score
- Progress charts: weight progression per exercise, volume trends, pain frequency timeline, risk score history
- Charts accessible from client profile

**Testing plan:**
- Risk score calculation is deterministic
- Risk factors explain the score correctly
- Risk score integrates with client score
- Charts render correctly with real data
- Charts handle edge cases (single data point, gaps in data)
- Total tests: ~20-25

**Milestone:** Risk scores visible on client profiles. Progress charts show meaningful trends.

---

## Phase 6a: Client App + Wearable Integration (Weeks 21-22)

**Goal:** Client-facing experience and recovery data integration.

**What gets built:**
- Client-facing app (separate user role)
- Client sees session history, goal progress, trainer-shared notes
- Whoop / Oura / Apple Watch OAuth integration
- Recovery/HRV data surfaced in briefing as additional layer (same-day only, never estimated)

**Milestone:** Clients can see their own training data. Wearable recovery data enhances briefings.

---

## Phase 6b: Multi-Trainer + Session Sharing + Scale (Weeks 23-24)

**Goal:** Multi-user support and growth features.

**What gets built:**
- Multi-trainer support for gyms
- Permission-based client access
- Session sharing: send session summary to client via email/SMS
- Client Health Profile: upload blood reports, body composition scans, medical notes — brain reasons over all of it
- Stripe billing when appropriate
- Offline support (record offline, queue for upload, local cache)
- Performance at 100+ trainers

**Milestone:** Platform supports multiple trainers. Sharing and health profiles working.

---

## Seed Data Strategy

**5 synthetic clients with varied session counts:**

| Client | Sessions | Purpose |
|--------|----------|---------|
| Client 1 | 1 | New client. Tests data maturity gates (no trends, briefing Layer 1 only). |
| Client 2 | 3 | Early client. Tests 2-3 session briefing behavior. |
| Client 3 | 5 | Moderate history. Tests basic pattern detection activation. |
| Client 4 | 10 | Established client. Tests full briefing layers, trend flags. |
| Client 5 | 15 | Long-term client. Tests rich trend analysis, cross-session patterns. |

Each client has:
- Varied exercise selection (legs, upper body push/pull, core)
- Mix of exercise cards and observation cards
- Pain mentions at different frequencies (none, occasional, recurring)
- Weight progression patterns (healthy, stagnant, too fast)
- Session plans for clients with 5+ sessions
- Form notes and coaching cues

---

## Total Test Count by Phase

- Phase 1a (Backend Foundation): ~60-80 tests
- Phase 1b (Voice Pipeline): ~30-40 tests
- Phase 2a (Mobile Core): ~20-25 tests
- Phase 2b (Detail + Flags): ~15-20 tests
- Phase 3a (Planning Flow): ~15-20 tests
- Phase 3b (Briefing): ~20-25 tests
- Phase 3c (The Brain): ~25-30 tests
- Phase 4a (Calendar + Auth): ~25-30 tests
- Phase 4b (Polish + Beta): ~15-20 tests
- Phase 5a (Score + Patterns): ~20-25 tests
- Phase 5b (Risk + Charts): ~20-25 tests

**Total at beta launch (Phase 4b): ~225-290 tests**
**Total at Phase 5b complete: ~265-340 tests**

Backend (pytest): ~180-230 tests
Mobile (Jest): ~85-110 tests
