# SuperTrainer

AI-powered coaching assistant that replaces the trainer's notebook. Record sessions by voice, get a structured timeline in real time, and let AI handle the data so the trainer can focus on coaching.

Personal trainers track everything — sets, reps, weights, form cues, pain flags, observations — across dozens of clients. Most still use paper notebooks or messy spreadsheets. SuperTrainer captures all of it from natural speech during the session itself, structures it automatically, and builds an intelligent picture of each client over time.

## What Works Today

- **Voice-to-timeline pipeline** — Trainer records a clip mid-session ("Sarah did 3 sets of squats at 60kg, RPE 7, knees were caving on the last set"). Deepgram transcribes, Claude extracts structured data via tool_use, validation normalizes exercise names and units. Result appears as an exercise card or observation card on the live timeline within seconds.
- **Inline editing** — Tap any card on the timeline to correct sets, weights, reps, form notes. Optimistic updates, no reload.
- **Session flow** — Start session → record clips → live timeline builds → end session → summary with workout classification (Upper/Lower/Full Body/Core) and exercise breakdown.
- **Compact exercise history** — Client profile shows past sessions with one-liner exercise summaries ("Goblet Squat: 20kg x10, 20kg x10, 20kg x8") matching how trainers actually write in notebooks.
- **Clarification handling** — When the parser isn't confident, the app flags it for the trainer to clarify or manually enter, rather than guessing wrong.
- **142 exercises** — Canonical exercise database with 3,466 aliases, fuzzy matching, and Deepgram keyterm prompting for gym vocabulary recognition.
- **734 backend tests** — Comprehensive coverage across all endpoints, services, and the full voice pipeline.

## How the Voice Pipeline Works

```
Trainer speaks → Audio clip uploaded
    → Deepgram Nova-3 (STT with gym keyterm prompting)
    → Claude (tool_use: exercise_card / observation_card / modify_exercise_card)
    → Validation (fuzzy exercise matching, weight normalization, pain extraction)
    → Persisted to DB → Live timeline update on phone
```

Each clip is additive — the parser sees the full session context and can modify previous entries ("actually that was 65kg not 60") or attach observations to specific sets.

## Coming Next (v1 — Notebook Replacement)

v1 goal: replace physical notebooks, GoodNotes, Notes app — or nothing at all. Must be simpler, cleaner, and faster.

- **Live exercise history** — Mid-session lookup: "what did this client do last time for squats?" Must be faster than flipping a page in GoodNotes. The #1 daily action (8-15 lookups per session).
- **Session planning** — Create, view, and modify plans from the app. End-session dictation: "anything for next time?" saves plan for next session.
- **Settings** — Weight unit preference (kg/lbs) for US trainers.
- **Session summaries** — 2-3 sentence AI recap per session. Read 3 lines, remember the whole session.
- **Flag system** — AI auto-assigns green/yellow/red flags on session save. Quick visual scanning of client health.
- **Pre-session briefings** — 4-layer AI summary: today's plan, last session recap, same-muscle-group history, trend flags.

Post-v1: The Brain (conversational RAG agent), pattern detection, progress charts, iPad layout.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **Mobile:** React Native + Expo (TypeScript), NativeWind, TanStack Query, Zustand
- **Voice:** Deepgram Nova-3 (STT) + Anthropic Claude (structured extraction via tool_use)
- **AI/RAG:** Anthropic Claude, OpenAI embeddings, pgvector (Phase 3)
- **Design:** Inter + JetBrains Mono typography, centralized token system
- **Hosting:** Railway (PostgreSQL + Redis + API)

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
