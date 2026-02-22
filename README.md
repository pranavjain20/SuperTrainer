# SuperTrainer

AI-powered coaching assistant for personal trainers. Trainers record sessions via voice, AI transcribes and structures data into a live session timeline, generates adaptive pre-session briefings with pattern detection and risk alerts, and provides a conversational agent ("The Brain") that answers any question about any client.

## Status

Phase 1a — Backend Foundation. Core data model (10 models), CRUD endpoints for clients, sessions, session entries, session plans, and injury flags. 262 tests passing. Voice pipeline, AI parsing, and The Brain are upcoming phases.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **Mobile:** React Native + Expo (TypeScript)
- **Voice:** Deepgram Nova-3 (STT) + Claude (structured extraction)
- **AI/RAG:** Anthropic Claude, OpenAI embeddings, pgvector
- **Auth:** Supabase Auth (Phase 4)
- **Hosting:** Railway

## Local Development

```bash
# Start PostgreSQL (dev on 5434, test on 5433)
docker compose up -d

# Set up backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -x -v
```

## Project Docs

- [`PRD.md`](PRD.md) — Product requirements and data model
- [`TECH_STACK.md`](TECH_STACK.md) — Technology choices with rationale
- [`BUILD_PLAN.md`](BUILD_PLAN.md) — 6-phase build plan
- [`STATUS.md`](STATUS.md) — Current progress
