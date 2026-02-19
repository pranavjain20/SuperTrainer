# SuperTrainer: Build Plan

---

## Timeline Overview

**MVP (voice loop works end-to-end on phone): Week 8**
**Beta-ready (intelligence + auth + polish): Week 14**
**Public launch: Week 16-18**

Total: ~4-4.5 months part-time (3-4 hrs/day from you, unlimited from Claude Code agents)

---

## How We Work Together

**Your role (3-4 hrs/day):**
- Review code I write (most important — you must understand everything)
- Make product decisions when I hit forks
- Test on your physical phone
- Write/refine sample transcripts (you know what trainers say, I don't)
- Approve or reject my architectural choices

**My role (Claude Code, 4 parallel agents):**
- Write code, tests, and iterate
- I can prepare multiple features in parallel while you sleep/study
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
F1: Data Models + Database
    ↓
    ├── F2: Client/Session CRUD API
    │       ↓
    │       ├── F5: Mobile — Client List + Session History screens
    │       │
    │       └── F3: Voice Pipeline (Deepgram STT + Claude Parser)
    │               ↓
    │               ├── F4: Audio Upload + Processing endpoint
    │               │       ↓
    │               │       └── F6: Mobile — Record + Review flow
    │               │
    │               └── F7: Intelligence Layer
    │                       ├── F7a: Pre-session Briefings
    │                       ├── F7b: Pattern Detection
    │                       └── F7c: Risk Scoring
    │                               ↓
    │                               └── F8: Mobile — Briefing + Dashboard screens
    │
    └── F9: Auth (Supabase) — can be added as middleware at any point
            ↓
            └── F10: Mobile Auth screens

F11: Polish, error handling, edge cases (throughout)
F12: App Store submission + landing page
```

**What can be parallelized:**
- Backend CRUD endpoints + Mobile app scaffolding (different agents, same week)
- Voice pipeline backend + Mobile client list UI (no dependency)
- Tests always written in parallel with implementation (TDD)
- Exercise database seeding + API endpoint development
- Auth integration (backend) + Auth screens (mobile) simultaneously

---

## Week-by-Week Plan

### WEEK 1: Project Setup + Data Models

**Goal:** Database is up, models are defined, migrations work, seed data exists.

**What gets built:**
- FastAPI project structure (app/, api/, services/, models, schemas)
- SQLAlchemy models: Trainer, Client, Session, ExerciseLog, InjuryFlag, ClientAnalysis, Exercise
- Alembic migrations setup + initial migration
- PostgreSQL on Railway provisioned and connected
- Seed script: 5 realistic clients with varied profiles
- Pydantic schemas for all request/response types
- Config management (pydantic-settings, env vars for API keys)

**Agent parallelization:**
- Agent 1: Models + database setup + migrations
- Agent 2: Pydantic schemas + config
- Agent 3: Seed script with realistic client data
- Agent 4: Project structure + Docker compose for local dev

**Your time this week:**
- Review data model design (~1 hr)
- Provide feedback on client profiles for seed data (~30 min)
- Review and approve all code (~2 hrs across the week)

**Testing plan:**
- Test: All models can be created and queried
- Test: Migrations run cleanly (up and down)
- Test: Seed script populates database correctly
- Test: All Pydantic schemas validate correctly (valid + invalid inputs)
- Test: Database constraints enforced (unique emails, FK integrity, check constraints)
- Test: JSONB fields serialize/deserialize correctly (sets data, cue effectiveness)
- Total tests: ~20-25

**Milestone:** `alembic upgrade head` runs clean, seed script creates 5 clients, all tests pass.

---

### WEEK 2: CRUD API Endpoints

**Goal:** Full REST API for clients and sessions. Any frontend can connect.

**What gets built:**
- Client endpoints: list, create, get, update, archive
- Session endpoints: create, get, list by client, update, delete
- Exercise log endpoints: list by session, list by client + exercise name
- Injury flag endpoints: list by client, create
- Standard response format: `{"data": ..., "meta": {...}}`
- Error handling middleware (consistent error responses)
- Pagination (cursor-based)
- Request logging middleware

**Agent parallelization:**
- Agent 1: Client endpoints + tests
- Agent 2: Session endpoints + tests
- Agent 3: Exercise log + injury flag endpoints + tests
- Agent 4: Middleware (error handling, logging, pagination utility)

**Your time this week:**
- Review API design decisions (~1 hr)
- Test endpoints manually via Swagger UI (~1 hr)
- Review all code (~2 hrs)

**Testing plan:**
- Test: Each endpoint returns correct status codes (200, 201, 404, 422)
- Test: List endpoints paginate correctly (cursor-based)
- Test: Create endpoints validate required fields
- Test: Update endpoints handle partial updates (PATCH)
- Test: Archive client doesn't delete data (soft delete)
- Test: Session list filtered by client_id
- Test: Exercise logs queryable by exercise name across sessions
- Test: Error responses match standard format
- Test: Invalid UUIDs return 404 not 500
- Test: Empty database returns empty lists, not errors
- Total tests: ~40-50

**Milestone:** Full Swagger docs at `/docs`, all CRUD operations work, all tests pass.

---

### WEEK 3: Voice Pipeline — Deepgram + Claude Parser

**Goal:** Upload audio → get structured session data back. This is the core technical bet.

**What gets built:**
- Deepgram service: audio file → transcript (with keyterm prompting for exercise names)
- Claude parser service: transcript → structured JSON (using tool_use)
- Parser prompt engineering (this takes the most iteration)
- Rule-based validation layer:
  - Exercise name normalization (fuzzy match to canonical database)
  - Weight unit detection and normalization
  - Implicit set expansion ("3 more sets at 145" → creates 3 set entries)
  - Pain report extraction with body part mapping
- Exercise database: JSON seed file with 100 exercises + aliases

**Agent parallelization:**
- Agent 1: Deepgram integration service + tests
- Agent 2: Claude parser service + prompt engineering
- Agent 3: Validation layer (exercise matching, weight normalization)
- Agent 4: Exercise database + seeding

**Your time this week:**
- Write 5-10 sample transcripts of what a trainer actually says (~2 hrs — this is critical, only you can do this)
- Review parser output on your transcripts and give feedback (~1 hr)
- Iterate on prompt with me (~1 hr)

**Testing plan:**
- Test: Deepgram returns transcript for clean audio file
- Test: Deepgram returns transcript for noisy audio file
- Test: Deepgram keyterm prompting improves exercise name recognition
- Test: Claude parser extracts exercises from simple transcript ("squats at 135 for 4 sets of 8")
- Test: Claude parser extracts multiple exercises from one transcript
- Test: Claude parser extracts form observations ("knee caving in")
- Test: Claude parser extracts pain reports ("hip is tight")
- Test: Claude parser extracts coaching cues ("push your knees out")
- Test: Claude parser extracts programming notes ("next time try 150")
- Test: Claude parser handles implicit sets ("3 more sets at 145")
- Test: Claude parser handles weight changes mid-exercise ("dropped to 135")
- Test: Claude parser handles RPE mentions ("that was about an RPE 8")
- Test: Validation layer normalizes "squat" → "barbell_back_squat"
- Test: Validation layer normalizes "deads" → "conventional_deadlift"
- Test: Validation layer converts "135 pounds" to kg internally
- Test: Validation layer handles ambiguous exercise names (flags for review)
- Test: End-to-end: raw audio file → complete structured JSON
- Test: Parser gracefully handles garbage/empty transcript
- Test: Parser handles transcript with no exercises (just chatting)
- Total tests: ~30-40

**Milestone:** Feed in a 5-minute training transcript, get back correctly structured exercises with 85%+ accuracy.

---

### WEEK 4: Audio Upload + Async Processing

**Goal:** Trainer uploads audio, gets immediate response, processing happens in background, results appear when ready.

**What gets built:**
- Supabase Storage integration (audio file upload via presigned URL)
- ARQ + Redis setup for async task queue
- Audio processing worker:
  1. Download audio from Supabase Storage
  2. Send to Deepgram → get transcript
  3. Send transcript to Claude parser → get structured data
  4. Validate and normalize
  5. Save to database (session, exercise_logs, injury_flags)
  6. Update session.processing_status
- Processing status endpoint (client polls for completion)
- Session creation flow: create session → upload audio → trigger processing → poll status → get results

**Agent parallelization:**
- Agent 1: Supabase Storage integration + file upload endpoint
- Agent 2: ARQ setup + worker definition
- Agent 3: Processing orchestration (the full pipeline in one worker task)
- Agent 4: Status polling endpoint + integration tests

**Your time this week:**
- Review async architecture (~1 hr)
- Test upload flow manually (~1 hr)
- Review code (~1-2 hrs)

**Testing plan:**
- Test: File upload to Supabase Storage succeeds
- Test: Presigned URL generation works
- Test: ARQ worker picks up queued job
- Test: Processing pipeline runs end-to-end (mock external APIs)
- Test: Processing pipeline handles Deepgram API failure (retry)
- Test: Processing pipeline handles Claude API failure (retry)
- Test: Processing status transitions: pending → processing → completed
- Test: Processing status transitions: pending → processing → failed (on error)
- Test: Failed job includes error message
- Test: Completed job creates exercise_logs in database
- Test: Completed job creates injury_flags for pain mentions
- Test: Concurrent uploads don't interfere with each other
- Test: Large audio file (30 min) doesn't timeout
- Test: Status polling endpoint returns correct state
- Total tests: ~20-25

**Milestone:** POST audio file → poll status → GET completed session with parsed exercises.

---

### WEEK 5: Mobile App — Foundation + Client Views

**Goal:** React Native app running on phone with client list and session history.

**What gets built:**
- React Native + Expo project initialization
- Navigation structure (tab navigator + stack navigators)
- API client service (Axios with base URL, error handling, retry)
- Client List screen (cards with name, last session, session count)
- Client Detail screen (profile info + session history list)
- Session Detail screen (exercise breakdown, form notes, pain reports)
- Pull-to-refresh on all list screens
- Loading states and error states for all screens
- TypeScript types matching backend Pydantic schemas

**Agent parallelization:**
- Agent 1: Expo project setup + navigation structure
- Agent 2: API client service + TypeScript types
- Agent 3: Client List + Client Detail screens
- Agent 4: Session Detail screen + shared components (cards, badges, loading states)

**Your time this week:**
- Install Expo Go on your phone, test throughout (~30 min setup)
- Review UI/UX on actual device (~1 hr/day)
- Make design decisions (colors, layout, what info to show) (~1 hr)

**Testing plan:**
- Test: App launches without crash
- Test: Client list loads and displays all clients
- Test: Client list shows correct last session date
- Test: Tapping client navigates to detail screen
- Test: Client detail shows session history in chronological order
- Test: Session detail shows all exercises with sets/reps/weight
- Test: Session detail shows form observations
- Test: Session detail shows pain reports with severity
- Test: Pull-to-refresh fetches updated data
- Test: Loading state shows while fetching
- Test: Error state shows when API is unreachable
- Test: Empty state shows when client has no sessions
- Test: Back navigation works correctly
- Total tests: ~15-20 (Jest + React Native Testing Library)

**Milestone:** Open app on phone → see client list → tap client → see session history → tap session → see full breakdown.

---

### WEEK 6: Mobile App — Voice Recording + Session Flow

**Goal:** Record a training session on the phone, upload, see results.

**What gets built:**
- Voice Recorder component (expo-av):
  - Start/stop/pause recording
  - Recording timer
  - Audio level visualization
  - Save as .m4a
- "New Session" flow:
  1. Select client from list
  2. Tap "Start Recording"
  3. Record (with timer and visual feedback)
  4. Tap "Stop"
  5. Show "Processing..." with progress
  6. Display parsed results
  7. Edit any field (inline editing)
  8. Tap "Confirm" to save
- Session review/edit screen:
  - Edit exercise name (dropdown from exercise database)
  - Edit weight, reps per set
  - Add/remove sets
  - Edit form notes
  - Add/remove pain reports

**Agent parallelization:**
- Agent 1: Voice Recorder component
- Agent 2: Recording flow screens (select client → record → processing)
- Agent 3: Session review/edit screen
- Agent 4: Upload service (audio → Supabase Storage → trigger processing → poll)

**Your time this week:**
- Test recording on your actual phone in different environments (~1 hr)
- Test the full flow end-to-end multiple times (~1 hr)
- Give UX feedback on the recording experience (~1 hr)
- Review code (~1 hr)

**Testing plan:**
- Test: Recording starts and stops cleanly
- Test: Recording produces valid audio file
- Test: Audio file uploads to Supabase Storage
- Test: Processing is triggered after upload
- Test: Status polling shows progress
- Test: Parsed results display correctly
- Test: Edit exercise name updates in state
- Test: Edit weight/reps updates in state
- Test: Add set appends to exercise
- Test: Remove set deletes from exercise
- Test: Confirm saves edited data to backend
- Test: Cancel discards changes
- Test: Recording while phone screen is off still works
- Test: Large recording (30 min) handles correctly
- Test: Network error during upload shows retry option
- Total tests: ~20-25

**Milestone:** Record audio on phone → wait for processing → see structured session → edit → save. This is the MVP moment.

---

### WEEK 7: MVP Hardening + Exercise Database

**Goal:** The core voice loop is bulletproof. Edge cases handled. Exercise matching is solid.

**What gets built:**
- Exercise database expanded to 200 exercises with aliases
- Fuzzy matching improvements (handle misspellings, abbreviations)
- Parser prompt refinement based on real usage in Week 6
- Error recovery flows:
  - What happens when Deepgram fails?
  - What happens when Claude fails?
  - What happens when upload fails mid-way?
  - What happens when user kills app during processing?
- Offline audio recording queue (record now, upload later)
- Session deletion and re-processing
- Comprehensive edge case testing

**Agent parallelization:**
- Agent 1: Exercise database expansion + fuzzy matching
- Agent 2: Error recovery flows + retry logic
- Agent 3: Offline queue for recordings
- Agent 4: Edge case test suite

**Your time this week:**
- Use the app as if you were a trainer for 30 min/day
- Record real-world-style sessions and report parser failures
- Prioritize which edge cases matter most

**Testing plan:**
- Test: Every exercise in database matches at least 3 aliases
- Test: Fuzzy match handles "bench" → "barbell_bench_press"
- Test: Fuzzy match handles "RDL" → "romanian_deadlift"
- Test: Fuzzy match handles misspelled exercise names
- Test: Deepgram failure triggers retry (up to 3 attempts)
- Test: Claude failure triggers retry (up to 3 attempts)
- Test: Both APIs failing returns clean error to user
- Test: Upload failure saves audio locally for retry
- Test: Offline recording queues and uploads when online
- Test: Re-processing a session replaces old parsed data
- Test: Deleting a session removes all associated exercise_logs and injury_flags
- Test: App handles 0 exercises in transcript gracefully
- Test: App handles 10+ exercises in one transcript
- Test: Parser handles mixed units in one transcript ("135 pounds... then 80 kilos")
- Test: 50 concurrent users don't degrade performance
- Total tests: ~25-30

**Milestone:** You've used the app for a full week. The core loop works reliably. Parser accuracy is 85%+. This is the MVP.

---

### WEEK 8: Intelligence — Pre-Session Briefings

**Goal:** Open a client and see an AI-generated briefing before their session.

**What gets built:**
- Briefing generation service:
  - Compile last 3-5 sessions into context
  - Include injury flags, pattern data, programming notes
  - Claude generates 4-6 sentence briefing
  - Cache result (invalidate when new session data arrives)
- Briefing API endpoint
- Mobile: Briefing card on Client Detail screen
  - Prominent placement at top
  - Shows risk level badge
  - Expandable for full details
  - "Refresh" button to regenerate
- Session context builder (compile relevant history for Claude prompt)

**Agent parallelization:**
- Agent 1: Briefing service + context builder
- Agent 2: Briefing API endpoint + caching
- Agent 3: Mobile Briefing card component
- Agent 4: Briefing quality tests (are the briefings actually useful?)

**Your time this week:**
- Read 10+ generated briefings and rate quality (~1 hr)
- Give feedback on briefing content (too long? too short? missing info?) (~1 hr)
- Review UI placement and design (~30 min)

**Testing plan:**
- Test: Briefing generates for client with 1 session
- Test: Briefing generates for client with 10 sessions
- Test: Briefing includes last session summary
- Test: Briefing mentions active injury flags
- Test: Briefing mentions programming notes from last session
- Test: Briefing mentions concerning patterns (if any)
- Test: Briefing is cached (second request is instant)
- Test: Cache invalidates when new session is saved
- Test: Briefing generation handles client with no sessions
- Test: Briefing renders correctly on mobile
- Test: Briefing risk badge shows correct color (green/yellow/red)
- Total tests: ~15-20

**Milestone:** Open client → see compelling briefing that would actually help a trainer prepare.

---

### WEEK 9: Intelligence — Pattern Detection + Risk Scoring

**Goal:** System automatically detects concerning patterns and scores injury risk.

**What gets built:**
- Pattern detection engine:
  - Weight progression analysis (per exercise, per client)
  - Pain frequency tracking (per body part)
  - Form quality trending (error rate over time)
  - Volume trend analysis (weekly totals)
- Risk scoring formula:
  - Weighted combination of pattern signals
  - Configurable thresholds
  - Outputs: score (0-100), level (low/medium/high), top risk factors
- ClientAnalysis table: auto-recompute after each session save
- Pattern alerts on Client Detail screen
- Dashboard screen: all clients sorted by risk level

**Agent parallelization:**
- Agent 1: Weight progression + volume analysis algorithms
- Agent 2: Pain frequency + form quality algorithms
- Agent 3: Risk scoring + ClientAnalysis recompute job
- Agent 4: Mobile dashboard screen + pattern alert components

**Your time this week:**
- Review pattern detection logic (does the math make sense?) (~1 hr)
- Review risk thresholds (is 5%/week too fast? too slow?) (~1 hr)
- Test dashboard with seeded data (~1 hr)

**Testing plan:**
- Test: Weight progression detects >5%/week as "too fast"
- Test: Weight progression detects <0.5%/week for 4 weeks as "stagnant"
- Test: Weight progression detects 2-3%/week as "healthy"
- Test: Pain frequency flags body part with 3+ occurrences
- Test: Pain frequency tracks severity trend (worsening vs stable)
- Test: Form quality detects increasing error rate over last 5 sessions
- Test: Volume analysis detects >10% week-over-week spike
- Test: Risk score calculation is deterministic (same input = same score)
- Test: Risk score handles client with only 1 session (insufficient data, not crash)
- Test: ClientAnalysis recomputes after session save
- Test: Dashboard sorts clients by risk level (high first)
- Test: Dashboard shows correct session count and last session date
- Test: Pattern alert shows on Client Detail when patterns detected
- Test: No false alerts on healthy client profile
- Total tests: ~25-30

**Milestone:** Dashboard shows all clients with risk indicators. Tap client → see patterns and risk factors.

---

### WEEK 10: Auth + Security

**Goal:** Real user accounts. Trainer can only see their own clients.

**What gets built:**
- Supabase Auth integration:
  - Email + password registration
  - Google OAuth
  - Apple OAuth (required for App Store)
  - Password reset flow
  - Email verification
- FastAPI auth middleware (verify JWT on every request)
- Trainer-scoped queries (all database queries filter by trainer_id)
- Mobile auth screens:
  - Login screen
  - Registration screen
  - Forgot password screen
  - OAuth buttons
- Secure token storage on mobile (expo-secure-store)
- Auto-refresh expired tokens

**Agent parallelization:**
- Agent 1: Supabase Auth setup + FastAPI middleware
- Agent 2: Trainer-scoped database queries (every endpoint)
- Agent 3: Mobile auth screens + navigation guards
- Agent 4: Security test suite

**Your time this week:**
- Test login/registration flow on phone (~1 hr)
- Test OAuth (Google) on phone (~30 min)
- Review security approach (~1 hr)

**Testing plan:**
- Test: Registration creates account in Supabase
- Test: Login returns valid JWT
- Test: Invalid credentials return 401
- Test: Expired token returns 401
- Test: Token refresh works
- Test: Authenticated request includes trainer_id
- Test: Trainer A cannot see Trainer B's clients
- Test: Trainer A cannot see Trainer B's sessions
- Test: Unauthenticated request returns 401 on all endpoints
- Test: Password reset sends email
- Test: Google OAuth returns valid session
- Test: Mobile stores token securely
- Test: App redirects to login when token missing
- Test: App redirects to login when token expired and refresh fails
- Test: Registration with existing email returns appropriate error
- Total tests: ~20-25

**Milestone:** Create account → login → see only your clients → logout → login again.

---

### WEEK 11-12: Polish + Edge Cases + Performance

**Goal:** App feels professional. No rough edges. Fast.

**What gets built:**
- Loading skeletons (not spinners) on all screens
- Error boundaries with retry buttons
- Empty states with helpful CTAs
- Haptic feedback on key actions (start/stop recording)
- Animation on transitions
- Performance optimization:
  - Database query optimization (N+1 checks, indexes)
  - API response time target: <200ms for CRUD, <500ms for briefings
  - Image/asset optimization
  - List virtualization for long session histories
- Push notifications:
  - "Session processed" notification
  - Daily briefing reminder (optional)
- Settings screen:
  - Weight unit preference (kg/lbs)
  - Notification preferences
  - Account management
- Onboarding flow:
  - First-time user experience
  - "Add your first client" prompt
  - "Record your first session" walkthrough

**Agent parallelization:**
- Agent 1: UI polish (loading states, empty states, animations)
- Agent 2: Performance optimization (queries, caching, indexes)
- Agent 3: Push notifications + settings screen
- Agent 4: Onboarding flow + comprehensive test sweep

**Your time this week:**
- Use the app daily as primary tester (~30 min/day)
- Report every rough edge, no matter how small
- Test on multiple network conditions (wifi, cellular, airplane mode)

**Testing plan:**
- Test: All screens show loading skeleton while fetching
- Test: All screens show error state with retry on failure
- Test: All list screens show empty state when no data
- Test: Weight displays in user's preferred unit
- Test: Changing unit preference updates all displayed weights
- Test: Push notification received when session processing completes
- Test: Onboarding flow guides new user to first recording
- Test: API endpoints respond in <200ms (p95) for CRUD
- Test: Briefing generation responds in <3 seconds (p95)
- Test: Client list with 50 clients scrolls smoothly
- Test: Session history with 100 sessions scrolls smoothly
- Test: App doesn't crash after 30 minutes of continuous use
- Test: Memory usage doesn't grow unbounded
- Total tests: ~20-25

---

### WEEK 13: Billing + Landing Page

**Goal:** People can pay us. People can find us.

**What gets built:**
- Stripe integration:
  - Free tier (5 clients, 10 sessions/month)
  - Pro tier ($X/month, unlimited) — price TBD based on research
  - Subscription management
  - Webhook handling (payment success, failure, cancellation)
- Free tier enforcement (API checks limits, shows upgrade prompt)
- Landing page:
  - Simple, clean, one-page
  - Hero: what it does (30-second video or animation)
  - How it works (3 steps)
  - Pricing
  - Sign up CTA
- App Store / Play Store prep:
  - EAS Build configuration
  - Screenshots
  - App description
  - Privacy policy

**Agent parallelization:**
- Agent 1: Stripe backend integration + webhook handler
- Agent 2: Free tier enforcement + upgrade prompts in mobile
- Agent 3: Landing page
- Agent 4: App Store prep + screenshots

**Your time this week:**
- Decide on pricing (~1 hr research + decision)
- Write app store description (~1 hr)
- Review landing page copy (~1 hr)

---

### WEEK 14: Beta Launch

**Goal:** 5-10 real trainers using the app.

**What gets done:**
- Final bug bash (use app for 2 hours straight, fix everything)
- Deploy backend to Railway production
- Submit to App Store / Play Store (or TestFlight for faster)
- Onboard 5-10 beta trainers:
  - Personal network, gym contacts, Reddit r/personaltraining
  - Walk each through setup (30 min each)
  - Set up feedback channel (WhatsApp group or Discord)
- Monitor:
  - Error rates (Sentry)
  - API performance
  - Parser accuracy on real data
  - User engagement (are they recording sessions?)

**Your time this week:**
- Personally onboard each beta user (~3-5 hrs total)
- Monitor feedback channel daily
- Prioritize reported issues

---

### WEEKS 15-18: Iterate on Feedback

What we build depends entirely on what beta users tell us. Likely:
- Parser accuracy improvements (top priority — every trainer will find cases it gets wrong)
- UX friction points we didn't anticipate
- Features they ask for that we haven't built
- Session sharing (email summaries to clients)
- Progress charts

---

## Total Test Count by Phase

- Week 1 (Models + DB): ~20-25 tests
- Week 2 (CRUD API): ~40-50 tests
- Week 3 (Voice Pipeline): ~30-40 tests
- Week 4 (Async Processing): ~20-25 tests
- Week 5 (Mobile Foundation): ~15-20 tests
- Week 6 (Voice Recording Flow): ~20-25 tests
- Week 7 (MVP Hardening): ~25-30 tests
- Week 8 (Briefings): ~15-20 tests
- Week 9 (Patterns + Risk): ~25-30 tests
- Week 10 (Auth): ~20-25 tests
- Week 11-12 (Polish): ~20-25 tests
- Week 13 (Billing): ~15-20 tests

**Total: ~265-335 tests at launch**

Backend (pytest): ~180-220 tests
Mobile (Jest): ~85-115 tests

---

## Key Risk Checkpoints

**End of Week 3 — CRITICAL CHECKPOINT:**
Does the parser work? If Claude can't reliably extract structured data from transcripts at 85%+ accuracy, we need to stop and fix the prompt/approach before building anything else. Everything downstream depends on this.

**End of Week 6 — MVP CHECKPOINT:**
Can you record on your phone, wait, and see correct results? If yes, we have a product. If not, we diagnose what's broken before adding intelligence features.

**End of Week 10 — BETA READINESS:**
Would you give this app to a trainer friend and not be embarrassed? If yes, we launch beta. If not, we take another week of polish.
