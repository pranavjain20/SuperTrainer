# SuperTrainer — Current Status

**Last updated:** Feb 20, 2026
**Current phase:** Phase 1a — Backend Foundation
**Next action:** Start Day 1 (Models + Migration)

---

## Phase 1a: Backend Foundation — IN PROGRESS

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

### Day 1: Models + Migration ← START HERE

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

### Day 2: Schemas + Test Infrastructure

Rewrite `schemas.py` for all 10 models. Add `EntryTypeEnum`. Update `conftest.py` table names (replace `exercise_logs` with `session_entries`, add `session_plans`, `brain_conversations`, `brain_messages`). Write schema validation tests.

### Day 3: Client + Session CRUD

Update `clients.py` and `sessions.py` for v3 schema. Add `scheduled_for`, `plan_id` to sessions. Update `main.py` (remove exercise_logs_router, add entries_router, plans_router). Delete old `test_exercise_logs.py`. Write client + session tests. ~40-50 total tests.

### Day 4: Session Entry CRUD

New `entries.py` (replaces `exercise_logs.py`). POST/GET for session entries with entry_type validation. Exercise cards require `exercise_name`, observation cards require `observation_text`. Auto-set `sequence_order`. List by session (ordered) and by client (paginated). ~55-65 total tests.

### Day 5: Session Plan + Injury Flag CRUD

New `plans.py`. Update `injury_flags.py` (`exercise_log_id` → `session_entry_id`). Plan CRUD: create, list by client, get, update. ~65-75 total tests.

### Day 6: Seed Script

Rewrite `seed.py`. 5 clients: 1/3/5/10/15 sessions. Mix of exercise_cards + observation_cards. Session plans for clients 3, 4, 5. Injury flags where appropriate. ~70-80 total tests.

### Day 7: Edge Cases + Integration Tests

Cross-endpoint integration. Edge case sweep: invalid UUIDs → 422, non-existent → 404, cross-entity ownership → 404, partial updates, empty DB handling, JSONB fields. ~75-85 total tests.

### Day 8: Coverage Audit + Polish

Audit every endpoint against test checklist. Fill gaps. Verify Swagger docs. Code review for DRY violations. ~80-90 total tests.

### Day 9: End-of-Phase Audit

Re-read every file. Check for hacks, missing error handling, FK validation gaps. Fix everything. Full test suite green.

### Day 10: Buffer + Phase Completion

Handle overflow. Update STATUS.md. Commit clean to feature branch. Present for review.

---

## Phase 1a Exit Criteria

- [ ] 10 models in models.py, all with correct fields and relationships
- [ ] pgvector enabled, embedding columns present
- [ ] Fresh Alembic migration runs clean
- [ ] All Pydantic schemas validate correctly
- [ ] Client CRUD: list, create, get, update, archive — all tested
- [ ] Session CRUD: create, get, list, update, delete — all tested
- [ ] Session Entry CRUD: create (both types), list by session, list by client — all tested
- [ ] Session Plan CRUD: create, get, list, update — all tested
- [ ] Injury Flag CRUD: create, list by client — all tested
- [ ] Seed script: 5 clients, 1/3/5/10/15 sessions, varied data — runs clean
- [ ] ~60-80+ tests all passing
- [ ] Swagger docs show all endpoints
- [ ] No 500s for any bad input (all proper 4xx)
- [ ] Cross-entity ownership validated everywhere
- [ ] Cascade deletes work and are tested
- [ ] Error format consistent: `{"error": {"code": "...", "message": "..."}}`
- [ ] End-of-phase audit completed honestly

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
