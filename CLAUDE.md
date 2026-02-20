# SuperTrainer — AI Training Intelligence Platform

## What This Is
AI-powered coaching assistant for personal trainers. Trainers record sessions via voice, AI transcribes + structures data, generates pre-session briefings with pattern detection and risk alerts.

## Current Status
**Phase: Pre-build. Planning complete.**
- No code written yet. Greenfield project.
- See STATUS.md for current task state.

## Key Documents
- `PRD.md` — Product requirements, features, build phases, data model
- `TECH_STACK.md` — Technology choices with rationale and alternatives
- `BUILD_PLAN.md` — Week-by-week plan, testing plan, agent parallelization
- `WORKFLOW.md` — Daily collaboration process, worktrees, communication protocol
- `AI_TRAINING_PLATFORM_DEEP_SPEC.md` — Original deep spec (reference)

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
- **Auth:** Supabase Auth (free tier)
- **File Storage:** Supabase Storage (free tier)
- **STT:** Deepgram Nova-3 (keyterm prompting for gym vocabulary)
- **LLM:** Anthropic Claude Sonnet (tool_use for structured extraction)
- **Hosting:** Railway

## Project Structure
```
super_trainer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (pydantic-settings, env vars)
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── models.py            # All SQLAlchemy models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── clients.py       # Client CRUD
│   │   │   ├── sessions.py      # Session endpoints
│   │   │   ├── voice.py         # Audio upload + processing
│   │   │   └── insights.py      # Briefings + patterns
│   │   ├── services/
│   │   │   ├── transcription.py # Deepgram STT integration
│   │   │   ├── parser.py        # Claude transcript parser
│   │   │   ├── briefing.py      # Pre-session briefing generation
│   │   │   └── patterns.py      # Rule-based pattern detection
│   │   └── seed.py              # Demo data seeding
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── tests/
├── mobile/                      # React Native + Expo app
├── tasks/
│   ├── todo.md                  # Current task checklist
│   └── lessons.md               # Mistakes and patterns learned
├── STATUS.md                    # Current state (updated every session)
└── CLAUDE.md                    # This file
```

## Commands
- `cd backend && uvicorn app.main:app --reload` — Run backend dev server
- `cd backend && alembic upgrade head` — Run migrations
- `cd backend && alembic revision --autogenerate -m "description"` — New migration
- `cd backend && pytest tests/ -x -v` — Run backend tests
- `cd mobile && npx expo start` — Run mobile app

## Git Strategy
- Main branch: always stable, reviewed, tests passing
- Feature branches: `feat/[component]-[feature]`
- Worktrees for parallel agent work (see WORKFLOW.md)
- Squash merge to main after review
- Never merge without all tests passing

## API Conventions
- All endpoints under `/api/v1/`
- Success: `{"data": ..., "meta": {...}}`
- Error: `{"error": {"code": "...", "message": "..."}}`
- HTTP status codes: 201 for creation, 422 for validation, 404 for not found
- Pagination: cursor-based `?cursor=...&limit=20`
- Weights stored in kilograms internally. Display conversion based on user preference.

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
