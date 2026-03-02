# SuperTrainer

AI-powered coaching assistant for personal trainers. Trainers record sessions via voice, AI transcribes and structures data into a live session timeline, generates adaptive pre-session briefings with pattern detection and risk alerts, and provides a conversational agent ("The Brain") that answers any question about any client.

## Status

Phase 1a (backend foundation), Phase 1b (voice pipeline), and Phase 2a (mobile app) complete and merged. Design system polish done. 734 backend tests passing.

Full voice-to-timeline pipeline working on phone: record clip → Deepgram STT → Claude parser → validation → live timeline with inline editing. End-session flow with workout classification, session summary. Centralized design token system with Inter + JetBrains Mono typography.

Next: planning discussion for remaining Phase 2b items and Phase 3 (Brain/RAG/patterns).

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

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0

# Tests
pytest tests/ -x -v

# Mobile
cd mobile
npm ci
npx expo start
```

## Project Docs

- [`docs/PRD.md`](docs/PRD.md) — Product requirements and data model
- [`docs/TECH_STACK.md`](docs/TECH_STACK.md) — Technology choices with rationale
- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) — 6-phase build plan
- [`STATUS.md`](STATUS.md) — Current progress
