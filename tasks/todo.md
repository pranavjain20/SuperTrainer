# SuperTrainer — Task Tracker

## Week 1-2: Backend Foundation (PRD v3 Rebuild)

### Models + Database
- [ ] New models.py with 10 models (trainers, clients, sessions, session_entries, session_plans, injury_flags, client_analysis, exercises, brain_conversations, brain_messages)
- [ ] New schemas.py for all request/response types
- [ ] Delete old Alembic migrations
- [ ] Enable pgvector extension + embedding columns for text-heavy fields
- [ ] Fresh Alembic migration for new schema
- [ ] Verify all models create and query correctly

### Seed Data
- [ ] New seed.py: 5 clients with 1/3/5/10/15 sessions (varied histories, pain mentions, progression patterns, observation cards)
- [ ] Seed session_plans for clients with 5+ sessions
- [ ] Seed injury_flags with varied body parts and pain levels

### CRUD Endpoints
- [ ] Client CRUD: list (cursor pagination, archive filter), create, get, update, archive + tests
- [ ] Session CRUD: create (with scheduled_for), get, list by client, update, delete + tests
- [ ] Session entry CRUD: create (exercise_card + observation_card types), list by session, list by client + tests
- [ ] Session plan CRUD: create, get by client, update + tests
- [ ] Injury flag CRUD: create, list by client + tests

### Infrastructure
- [ ] Update main.py router imports for new endpoint modules
- [ ] Update conftest.py for new table names (session_entries replaces exercise_logs)
- [ ] Verify error handling middleware works with new endpoints
- [ ] Verify request logging middleware works

### Verification
- [ ] All tests pass (`pytest tests/ -x -v`)
- [ ] Swagger docs show all endpoints correctly
- [ ] Seed script populates database correctly
- [ ] End-of-day audit: re-read every file, check for hacks, run full suite
