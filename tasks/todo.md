# SuperTrainer — Task Tracker

## Week 1-2: Backend Foundation (PRD v3 Rebuild)

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
- [x] New seed.py: 5 clients with 1/3/5/10/15 sessions (varied histories, pain mentions, progression patterns, observation cards)
- [x] Seed session_plans for clients with 5+ sessions (Aisha: 1, Jake: 2, Elena: 3)
- [x] Seed injury_flags with varied body parts and pain levels (Marcus: knee, Jake: back, Elena: shoulder resolved + hip active)
- [x] Seed 19 canonical exercises in Exercise table
- [x] 10 seed tests (counts, relationships, idempotency)

### Day 8: Coverage Audit + Polish
- [x] Fix Session.trainer_id missing ondelete="CASCADE"
- [x] Fix BrainMessage.trainer_id missing ondelete="CASCADE"
- [x] Fix SessionPlan.trainer_id DB out of sync (code had CASCADE, DB didn't)
- [x] Alembic migration for FK cascade fixes
- [x] Consolidate 3 ownership validators into dependencies.py
- [x] Replace response_model=dict with DataResponse[XResponse] on all 14 single-resource endpoints
- [x] Fix injury_flags tag (dashes → underscores)
- [x] Clean unused imports (clients.py, entries.py, plans.py)
- [x] Test: plan delete leaves siblings intact
- [x] Test: trainer cascade deletes sessions (validates FK fix)
- [x] Test: injury flag rejects entry from wrong session
- [x] 295 tests passing

### Day 9: End-of-Phase Audit
- [x] Full codebase read: every source file, test file, infrastructure file
- [x] Fix cross-type contamination bug on PATCH /entries (route-level validation)
- [x] Add resolved_at validation on InjuryFlagUpdate (model_validator)
- [x] Add return type annotation to health_check()
- [x] Check off all 17 Phase 1a exit criteria in STATUS.md
- [x] 6 new tests (2 edge case, 2 injury flag API, 3 schema)
- [x] 301 tests passing

### Day 10: Golden Audit + Phase Completion
- [x] Extract pagination helper (DRY — 5 services → 1 shared function)
- [x] Fix alembic/env.py to read DATABASE_URL from settings
- [x] Fix plan_service.update_plan to allow nulling planned_for_date
- [x] Add 5 missing tests (empty sets, empty goals, null date PATCH, error response structure)
- [x] Full codebase audit: two agents, every source + test file — clean
- [x] Squash merge feat/phase-1a-backend → master
- [x] 306 tests passing on master

### Verification
- [x] All tests pass — 306 green (pytest tests/ -x -v)
- [x] Swagger docs: all endpoints typed correctly with DataResponse[XResponse], tags consistent
- [x] Seed script populates database correctly (34 sessions, 115 entries, 19 exercises, 6 plans, 4 injuries)
- [x] End-of-day audit: Day 5 Golden Audit complete
- [x] End-of-phase audit: Day 9 complete, all exit criteria met
- [x] Day 10 golden audit complete, merged to master
