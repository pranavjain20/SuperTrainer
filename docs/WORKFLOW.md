# SuperTrainer: Project Workflow

Project-specific collaboration details. For general session protocol and engineering preferences, see `~/.claude/CLAUDE.md`.

---

## Test Commands

```bash
# Backend tests (from project root)
cd backend && .venv/bin/pytest tests/ -x -v

# Mobile tests (from project root)
cd mobile && npm test

# Run backend dev server (--host 0.0.0.0 required for phone access)
cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0

# Run mobile dev server
cd mobile && npx expo start
```

---

## Environment Setup

### Docker (PostgreSQL)
```bash
docker compose up -d
```
- **Dev DB:** port 5434
- **Test DB:** port 5433
- **Native Postgres conflict:** Pranav has native Postgres on port 5432 — Docker uses 5434/5433 to avoid collision.

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```
**Note:** Pin `greenlet>=3.0,<3.2` if pydantic/greenlet break after a clean venv (v3.3+ breaks SQLAlchemy).

### Mobile
```bash
cd mobile
npm ci    # Use npm ci, not npm install — exact lockfile versions
npx expo start
```
Phone must be on same WiFi as laptop. API points to `192.168.1.160:8000` (hardcoded in `src/constants/config.ts` — update if IP changes).

**If node_modules breaks** (Expo hangs on "Starting project" or missing module errors):
```bash
cd mobile
rm -rf node_modules .expo
git checkout HEAD -- package-lock.json
npm ci
npx expo start
```

---

## Branch Naming Convention

```
feat/[component]-[feature]     → New features
fix/[component]-[description]  → Bug fixes
test/[component]-[what]        → Test additions
refactor/[component]-[what]    → Refactors

Examples:
feat/backend-session-entries
feat/mobile-session-timeline
feat/pipeline-per-clip-parser
fix/parser-weight-normalization
```

## Merge Rules

- Never merge directly to main without review
- All tests must pass on the branch before merge
- Squash merge for clean history (one commit per feature)
- Main branch must always be in a working state
- Docs (STATUS.md, devlogs, todo.md) go on master. Code goes on feature branch.

---

## Git Worktree Strategy

Worktrees let you check out multiple branches in separate directories simultaneously. Each Claude Code agent works in its own worktree — zero conflicts.

### Directory Structure

```
~/Desktop/supertrainer/              ← main branch (stable, reviewed, merged code)
~/Desktop/supertrainer-worktrees/
    ├── wt-backend/                   ← Backend feature branch
    ├── wt-mobile/                    ← Mobile feature branch
    ├── wt-pipeline/                  ← Voice pipeline feature branch
    └── wt-tests/                     ← Test suite branch
```

### When Worktrees Are Most Valuable

**High parallelization phases:**
- Phase 1, Week 1-2: 4 endpoint groups built simultaneously
- Phase 1, Week 3-4: Deepgram + Claude parser + exercise DB + validation
- Phase 2, Week 5-6: Mobile screens built in parallel
- Phase 5: Pattern detection algorithms (all independent)

**Low parallelization phases:**
- Phase 2, Week 7: Sequential refinement
- Phase 4, Week 14: Auth touches every endpoint

---

## Feature Dependency Map

```
Phase 1: Backend Foundation + Voice Pipeline (COMPLETE)
    ├── 10 Models + CRUD + 306 tests
    └── Voice Pipeline (Deepgram + Claude + validation) + 683 tests

Phase 2: Mobile App (2a COMPLETE, 2b partially built)
    ├── Navigation, Home, Clients, Profile, Session recording
    ├── Voice pipeline integration, inline editing, clarification UX
    └── 734 total backend tests

Phase 3: Pre-Session Context + The Brain
    ├── Planning flow, 4-layer briefing, push notifications
    └── The Brain (RAG + conversational agent)

Phase 4: Calendar + Auth + Launch Prep
Phase 5: Intelligence Layer (scores, patterns, charts)
Phase 6: Growth Features (client app, multi-trainer)
```

---

## Deployment

**Hosting:** Railway (PostgreSQL + Redis + API). Deployment process TBD — not yet configured for production.
