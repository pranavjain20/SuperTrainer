# SuperTrainer — AI Training Intelligence Platform

## What This Is
AI-powered coaching assistant for personal trainers. Trainers record sessions via voice (per-clip, real-time), AI transcribes + structures data into a live session timeline (exercise cards + observation cards). Generates adaptive pre-session briefings with pattern detection and risk alerts. Conversational AI agent ("The Brain") answers any question about any client, creates and modifies session plans.

## Current Status
**Phase: PRD v3 Rebuild — Documentation complete, starting Week 1-2 backend.**
- See STATUS.md for current task state.
- See docs/PRD.md for full product requirements.

## Key Documents
- `docs/PRD.md` — Product requirements, features, build phases, data model
- `docs/TECH_STACK.md` — Technology choices with rationale and alternatives
- `docs/BUILD_PLAN.md` — 6-phase (13 sub-phase) build plan, testing plans, agent parallelization
- `docs/WORKFLOW.md` — Daily collaboration process, worktrees, communication protocol
- `reference/PRD_v1.md` — Original PRD (historical reference)
- `reference/AI_TRAINING_PLATFORM_DEEP_SPEC.md` — Original deep spec (historical reference)

## Session Protocol
- On session start: read STATUS.md, tell Pranav what needs review and what's next
- On session end: update STATUS.md with completed work, pending reviews, blockers
- Track tasks in tasks/todo.md
- Log lessons learned in tasks/lessons.md

## Tech Stack
- **Mobile:** React Native + Expo (TypeScript)
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic
- **Database:** PostgreSQL on Railway
- **Task Queue:** ARQ + Redis on Railway
- **Auth:** Supabase Auth (free tier) — Phase 4
- **File Storage:** Supabase Storage (free tier)
- **STT:** Deepgram Nova-3 (keyterm prompting for gym vocabulary)
- **LLM:** Anthropic Claude Sonnet (tool_use for structured extraction; hybrid RAG for The Brain)
- **Embeddings:** OpenAI text-embedding-3-small (pgvector semantic search)
- **Push Notifications:** Expo Push Notifications
- **Web Search:** Tavily API (Phase 3+ — Brain State 3 fallback)
- **Calendar:** Google Calendar API + Apple CalDAV (Phase 4)
- **Hosting:** Railway

## Project Structure
```
supertrainer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (pydantic-settings, env vars)
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── models.py            # All SQLAlchemy models (10 models)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── clients.py       # Client CRUD
│   │   │   ├── sessions.py      # Session CRUD
│   │   │   ├── entries.py       # Session entry CRUD (exercise_card + observation_card)
│   │   │   ├── plans.py         # Session plan CRUD
│   │   │   ├── injuries.py      # Injury flag CRUD
│   │   │   ├── voice.py         # Per-clip audio processing
│   │   │   ├── insights.py      # Briefings + patterns
│   │   │   ├── agent.py         # Brain conversational agent
│   │   │   └── calendar.py      # Calendar integration (Phase 4)
│   │   ├── services/
│   │   │   ├── transcription.py # Deepgram STT integration
│   │   │   ├── parser.py        # Claude transcript parser (per-clip)
│   │   │   ├── briefing.py      # Pre-session briefing generation (4-layer)
│   │   │   ├── patterns.py      # Rule-based pattern detection
│   │   │   ├── brain.py         # The Brain — RAG + conversational agent
│   │   │   └── calendar.py      # Calendar sync service (Phase 4)
│   │   └── seed.py              # Demo data seeding
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── tests/
├── mobile/                      # React Native + Expo app
├── tasks/
│   ├── todo.md                  # Current task checklist
│   └── lessons.md               # Mistakes and patterns learned
├── docs/                        # Project documentation
│   ├── PRD.md                   # Product requirements
│   ├── BUILD_PLAN.md            # Build plan
│   ├── TECH_STACK.md            # Technology choices
│   ├── WALKTHROUGH.md           # System walkthrough
│   └── WORKFLOW.md              # Collaboration process
├── reference/                   # Historical documents
│   ├── PRD_v1.md
│   └── AI_TRAINING_PLATFORM_DEEP_SPEC.md
├── concepts/                    # Daily learning documents
│   ├── index.md                 # Concepts index
│   └── YYYY-MM-DD.md            # Per-day entries
├── devlog/                      # Daily build journal
│   └── YYYY-MM-DD.md            # Per-day entries
├── STATUS.md
└── CLAUDE.md                    # This file
```

## Data Model (10 Models)

**trainers** — id, email, name, phone, tier, supabase_user_id (Phase 4), created_at, last_login

**clients** — id, trainer_id, name, email, phone, birth_date, training_start_date, goals[], injury_history, archived, created_at

**sessions** — id, trainer_id, client_id, started_at, ended_at, scheduled_for, duration_minutes, audio_url, audio_duration_seconds, raw_transcript, processing_status, trainer_edited, plan_id (FK → session_plans, nullable), created_at, updated_at

**session_entries** — id, session_id, client_id, entry_type (exercise_card | observation_card), sequence_order, exercise_name, exercise_canonical, sets (JSONB), total_volume_kg, form_notes[], cues_given[], cue_effectiveness (JSONB), observation_text, attached_to_set, flag_color, flag_reason, performed_at, created_at

**session_plans** — id, client_id, trainer_id, plan_text, planned_for_date, created_at

**injury_flags** — id, client_id, session_id, session_entry_id (nullable), body_part, pain_level (1-10), description, first_occurrence, last_occurrence, occurrence_count, resolved, resolved_at, flagged_at

**client_analysis** — id, client_id, total_sessions, last_session_date, avg_weight_increase_pct_per_week, current_volume_trend, injury_risk_score, injury_risk_level, risk_factors[], form_degradation_detected, overtraining_indicators, pain_pattern_detected, client_score (0-100), client_score_breakdown (JSONB), last_computed_at

**exercises** — id, canonical_name, aliases[], category, primary_muscles[], equipment[], difficulty, common_errors (JSONB), created_at

**brain_conversations** — id, trainer_id, title (auto-generated), created_at, updated_at

**brain_messages** — id, conversation_id, trainer_id, role (user | assistant), content, created_at

## Commands
- `cd backend && uvicorn app.main:app --reload` — Run backend dev server
- `cd backend && alembic upgrade head` — Run migrations
- `cd backend && alembic revision --autogenerate -m "description"` — New migration
- `cd backend && pytest tests/ -x -v` — Run backend tests
- `cd mobile && npx expo start` — Run mobile app

## Git Strategy
- Main branch: always stable, reviewed, tests passing
- Feature branches: `feat/[component]-[feature]`
- Worktrees for parallel agent work (see docs/WORKFLOW.md)
- Squash merge to main after review
- Never merge without all tests passing

## API Conventions
- All endpoints under `/api/v1/`
- Success: `{"data": ..., "meta": {...}}`
- Error: `{"error": {"code": "...", "message": "..."}}`
- HTTP status codes: 201 for creation, 422 for validation, 404 for not found
- Pagination: cursor-based `?cursor=...&limit=20`
- Weights stored in kilograms internally. Display conversion based on user preference.

## Code Quality Philosophy

The goal is code that a great engineer would enjoy reading. Not clever code, not over-abstracted code — clean code where every piece is obvious, intentional, and earns its place.

- **Readability is the measure.** If someone has to re-read a function to understand it, it's too complex — whether that's because it's too long, too nested, too clever, or poorly named. Use judgment, not line counts.
- **Each function does one thing you can name.** If you need "and" to describe it, consider splitting. But don't split just to be short — two tangled halves are worse than one clear whole.
- **Flat over nested.** Early returns, guard clauses, extract-and-name. If logic is three levels deep, there's almost always a cleaner way.
- **Names are documentation.** `get_client_by_id`, not `get_cli`. `is_archived`, not `archived_flag`. Consistent verbs across the codebase — if one service uses `create_`, they all do.
- **No dead weight.** No commented-out code, no unused imports, no placeholder functions, no `Any` types without genuine need. If it's not pulling its weight, delete it.
- **Files stay cohesive.** One domain per file. When a file starts feeling like it covers too many concerns, split by responsibility — not by arbitrary size.
- **Type hints on all function signatures.** Including return types. This is a typed codebase.
- **Tests read like specs.** Name describes the behavior (`test_injury_flag_rejects_pain_level_above_10`), one logical assertion per test, arrange-act-assert flow.

## Build Discipline

IMPORTANT: This is a real product. Early days are the foundation — if the foundation is shaky, everything built on top will be fragile. No hacks. No shortcuts. No "good enough for now."

YOU MUST do the end-of-day audit automatically. Pranav should never have to ask "did you check everything?" — that check is your job, every time.

### Write a Little, Test a Little
- Build incrementally: implement one small piece, write its tests, verify it passes, then move on.
- Never batch up a ton of untested code. If you wrote more than ~30 lines without running tests, stop and test what you have.
- Every new function gets at least one happy-path test and one edge-case test before moving to the next function.

### End-of-Day Audit (MANDATORY — do this automatically, not when asked)
After finishing each day's work, before saying "done":
1. **Re-read every file you touched.** Look for:
   - Hacks, workarounds, or "temporary" solutions that should be done properly
   - Copy-pasted code that should be extracted
   - Missing error handling or edge cases
   - Inconsistencies with existing patterns
   - Data integrity gaps (e.g. FK references not validated, cross-entity ownership not checked)
   - Responses that could be 500s instead of proper 4xx errors
2. **If you find a hack, fix it now.** Don't defer. Don't leave TODOs. Do it the right way or don't do it at all. Keep iterating until it's right.
3. **Run the full test suite**, not just the new tests. Confirm nothing regressed.
4. **Audit test coverage ruthlessly.** For every endpoint, ask:
   - Happy path tested?
   - Every validation/error path tested? (404, 422, missing fields, empty strings, out-of-range values)
   - Cross-entity relationships tested? (does X belong to Y?)
   - Cascade deletes tested and verified?
   - Pagination tested with actual cursor passing?
   - Partial updates tested? (send one field, verify others unchanged)
5. **Report findings honestly** — list what you found and fixed, not just "all good."

### Be Your Own Harshest Reviewer
- After writing code, switch to reviewer mindset. Ask: "If a staff engineer reviewed this, what would they flag?"
- Check every validation path: can a bad input cause a 500 instead of a 4xx?
- Check every FK reference: if user passes an ID, do we validate it exists AND belongs to the right parent?
- Check every delete: do cascades actually work? Is there a test proving it?
- If you wouldn't ship it to production, don't call it done.

### No Hacking Through Blockers
- If something doesn't work, find the root cause. Don't add workarounds.
- If a test fails, understand WHY before fixing it. Don't just tweak until it passes.
- If you're stuck, stop and re-plan rather than forcing a brittle solution.
- Ask Pranav if genuinely unsure — a 30-second question beats an hour of wrong-direction work.

### Verification
- Backend changes: run `cd backend && pytest tests/ -x -v`
- Mobile changes: run `cd mobile && npm test`
- If no tests exist yet: write at least 2 tests first, then make them pass
- Never say "done" without running the full suite and seeing all green.

## API Keys Needed
- **Deepgram:** deepgram.com — $200 free credit (STT)
- **Anthropic Claude:** console.anthropic.com — API key (~$5-10 during dev)
- **Supabase:** supabase.com — free tier (auth + storage)
- **Railway:** railway.app — $5/month hobby plan (hosting + DB + Redis)
- **Tavily:** tavily.com — API key (Phase 3+, web search for Brain State 3)
