# SuperTrainer — Task Tracker

## Phase 1b: Voice Pipeline (Week 3-4)

### Day 1: Exercise Database + Deepgram Service
- [ ] Expand exercises from 19 → ~100 (aliases, categories, muscles, equipment)
- [ ] Select top 100 keyterms for Deepgram prompting (API limit: 100)
- [ ] Create `services/transcription.py` — Deepgram STT integration (async, error handling)
- [ ] Add `deepgram-sdk` to requirements.txt
- [ ] Unit tests: Deepgram service with mocked API responses

### Day 2: Claude Parser — Tool Schema + Core Parsing
- [ ] Design tool_use schema matching SessionEntry model (exercise_card + observation_card tools)
- [ ] Write system prompt for parser
- [ ] Create `services/parser.py` — Claude transcript → structured data via tool_use
- [ ] Core parsing: single exercises, basic set/rep/weight extraction
- [ ] Add `anthropic` to requirements.txt
- [ ] Unit tests: parser with mocked Claude responses

### Day 3: Parser — Intent Classification + Additive Parsing + Context
- [ ] Intent classification: new exercise vs additive vs observation vs correction
- [ ] Additive parsing: "also, sets 2 through 4 were at RPE 8" modifies existing card
- [ ] Session context: resolve references ("same weight", "dropped to 75") using prior entries
- [ ] Tests: intent classification, additive parsing, context resolution

### Day 4: Validation Layer
- [ ] Create `services/validation.py` — fuzzy match exercise names to canonical DB (rapidfuzz)
- [ ] Weight normalization: "185 pounds" → 83.9 kg, "80 kilos" → 80.0 kg
- [ ] Set expansion: "3 sets of 10 at 80" → 3 individual set records
- [ ] Pain extraction: detect pain/injury mentions, map body parts, extract severity
- [ ] Add `rapidfuzz` to requirements.txt
- [ ] Tests: fuzzy matching, weight conversion, set expansion, pain extraction

### Day 5: Voice Clip Endpoint + Integration Tests
- [ ] Create `api/voice.py` — `POST /api/v1/sessions/{session_id}/voice-clip`
- [ ] Wire Deepgram → parser → validation pipeline
- [ ] Return structured entry + timing breakdown (transcription_ms, parsing_ms, validation_ms)
- [ ] Register voice router in main.py
- [ ] Integration tests: full pipeline with mocked external APIs

### Day 6: Real Transcript Testing + Prompt Tuning
- [ ] Pranav writes 5-10 sample transcripts of real trainer speech
- [ ] Test parser against real speech patterns
- [ ] Tune system prompt based on failures
- [ ] Handle gym patterns: "sets 2 through 4 at 85 kilos for 8", "dropped to 75", "superset with curls"
- [ ] Iterate until ≥85% of test transcripts parse correctly

### Day 7: Embeddings + Full Test Suite + Audit
- [ ] Embedding generation prep for Phase 3c
- [ ] Update seed.py with expanded exercise database
- [ ] Complete test suite (target: 30-40 new tests)
- [ ] End-of-phase audit: re-read every file, adversarial review, full suite green
- [ ] All Phase 1b exit criteria met

### Exit Criteria
- [ ] ≥85% of test transcripts parsed correctly
- [ ] ≥90% exercise names normalized to canonical
- [ ] ≥95% set/reps extracted correctly
- [ ] ≥90% weights extracted correctly
- [ ] Additive parsing works on all correction test cases
- [ ] Response time ≤3 seconds per clip
- [ ] 30-40 new tests, all green
- [ ] End-of-phase audit completed

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
