# SuperTrainer — AI Training Intelligence Platform

## What This Is
AI-powered coaching assistant for personal trainers. Trainers record sessions via voice (per-clip, real-time), AI transcribes + structures data into a live session timeline (exercise cards + observation cards). Generates adaptive pre-session briefings with pattern detection and risk alerts. Conversational AI agent ("The Brain") answers any question about any client, creates and modifies session plans.

## Current Status
**Phase 1a (backend), 1b (voice pipeline), 2a (mobile app) COMPLETE. Design system polish done. 734 tests.**
- See STATUS.md for current task state.
- See docs/PRD.md for full product requirements.
- v1 scope finalized (Apr 3, 2026). Target: replace the trainer's notebook. See tasks/todo.md for full breakdown.
- Next: compact format visual review on phone, then build live exercise history.

## Key Documents
- `docs/PRD.md` — Product requirements, features, build phases, data model
- `docs/TECH_STACK.md` — Technology choices with rationale and alternatives
- `docs/BUILD_PLAN.md` — 6-phase (13 sub-phase) build plan, testing plans, agent parallelization
- `docs/WORKFLOW.md` — Daily collaboration process, worktrees, communication protocol
- `reference/PRD_v1.md` — Original PRD (historical reference)
- `reference/AI_TRAINING_PLATFORM_DEEP_SPEC.md` — Original deep spec (historical reference)

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
│   ├── RESEARCH.md              # Domain research
│   ├── PITCH.md                 # Business pitch + market data
│   ├── DESIGN.md                # Visual design system spec
│   ├── guides/                  # Per-phase learning guides
│   │   ├── phase-1a.md          # Backend foundation walkthrough
│   │   ├── phase-1b.md          # Voice pipeline walkthrough
│   │   └── phase-2a.md          # Mobile app walkthrough
│   └── WORKFLOW.md              # Project-specific workflow
├── reference/                   # Historical documents
│   ├── PRD_v1.md
│   ├── AI_TRAINING_PLATFORM_DEEP_SPEC.md
│   └── WHY_NOW.md
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

## API Conventions
- All endpoints under `/api/v1/`
- Success: `{"data": ..., "meta": {...}}`
- Error: `{"error": {"code": "...", "message": "..."}}`
- HTTP status codes: 201 for creation, 422 for validation, 404 for not found
- Pagination: cursor-based `?cursor=...&limit=20`
- Weights stored in kilograms internally. Display conversion based on user preference.

## Mobile Design System

All mobile UI must use the centralized design token system. No ad-hoc colors, font sizes, or spacing values.

- **Colors:** Import from `src/constants/tokens.ts` (`colors.bg.*`, `colors.text.*`, `colors.border.*`, `colors.blue.*`, etc.). Never use raw hex strings.
- **Typography:** Use `<ThemedText variant="...">` from `src/components/ThemedText.tsx`. Variants: `display`, `title-1`, `title-2`, `title-3`, `body`, `body-medium`, `body-small`, `caption`, `data`, `data-bold`. Never use raw `<Text>` with inline font styles.
- **Fonts:** Inter (Regular/Medium/SemiBold/Bold) for UI text, JetBrains Mono (Regular/Bold) for data/numbers.
- **Spacing:** Use Tailwind classes (`px-4`, `mt-3`, `mb-2`) or token values. Keep spacing consistent with existing components.

## API Keys Needed
- **Deepgram:** deepgram.com — $200 free credit (STT)
- **Anthropic Claude:** console.anthropic.com — API key (~$5-10 during dev)
- **Supabase:** supabase.com — free tier (auth + storage)
- **Railway:** railway.app — $5/month hobby plan (hosting + DB + Redis)
- **Tavily:** tavily.com — API key (Phase 3+, web search for Brain State 3)

---

For workflow protocol, session rules, and engineering preferences, see `~/.claude/CLAUDE.md`. For document specs and routing rules, see `~/.claude/project-playbook.md`.
