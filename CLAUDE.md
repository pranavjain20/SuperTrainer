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

## Verification Rule

IMPORTANT: Test-driven development. Before building any new feature, write the tests first. Tests must fail before implementation begins. Implementation is complete only when tests pass.

After every feature, verify it works before saying "done."
- Backend changes: run `cd backend && pytest tests/ -x -v`
- Mobile changes: run `cd mobile && npm test`
- If no tests exist yet: write at least 2 tests first, then make them pass
- Never say "done" without running verification.

## API Keys Needed
- **Deepgram:** deepgram.com — $200 free credit (STT)
- **Anthropic Claude:** console.anthropic.com — API key (~$5-10 during dev)
- **Supabase:** supabase.com — free tier (auth + storage)
- **Railway:** railway.app — $5/month hobby plan (hosting + DB + Redis)
