# SuperTrainer: Daily Workflow

## How Our Collaboration Works

### The STATUS.md System

At the end of every working session, I update `STATUS.md` in the project root. This file always contains:

1. **What was completed** — features built, tests passing
2. **What needs your review** — branches ready for you to look at, with what to focus on
3. **What's blocked on you** — decisions I need, transcripts I need you to write, things only you can test
4. **What I'm working on next** — so you know what's coming
5. **Current test count** — how many tests exist and pass

### Your Morning Routine

1. Open terminal
2. `cd ~/Desktop/supertrainer`
3. Launch Claude Code
4. Say: **"What's the status?"**
5. I read STATUS.md and walk you through everything

That's it. I handle the context restoration, you just ask.

### Your Review Process

When I say "branch X is ready for review":

1. I'll show you the key files and explain what I built
2. You read the code (you need to understand everything — this is your product)
3. You run it / test it on your phone
4. You say "looks good" or "change X"
5. I merge to main or fix and come back

### End of Session

When you're done for the day, just say **"I'm done for today"** and I will:
1. Update STATUS.md with current state
2. Update CLAUDE.md if any key decisions were made
3. Commit all work-in-progress to appropriate branches
4. List what I'll prepare for your next session

---

## Git Worktree Strategy

### What Are Worktrees?

Normally, git only lets you have one branch checked out at a time. Worktrees let you check out multiple branches in separate directories simultaneously. Each Claude Code agent works in its own worktree — zero conflicts.

### Directory Structure

```
~/Desktop/supertrainer/              ← main branch (stable, reviewed, merged code)
~/Desktop/supertrainer-worktrees/
    ├── wt-backend/                   ← Backend feature branch
    ├── wt-mobile/                    ← Mobile feature branch
    ├── wt-pipeline/                  ← Voice pipeline feature branch
    └── wt-tests/                     ← Test suite branch
```

### How It Works in Practice

**Example: Phase 1, Week 3-4 (Voice Pipeline)**

I spin up 4 agents, each in a different worktree:

```
Agent 1 → wt-backend/   → branch: feat/deepgram-service
Agent 2 → wt-pipeline/  → branch: feat/claude-parser
Agent 3 → wt-backend/   → branch: feat/exercise-database
Agent 4 → wt-tests/     → branch: feat/parser-tests
```

Each agent writes code and commits to their branch. When you review:

1. I show you what each branch does
2. You review the code
3. I merge each approved branch into main
4. I rebase remaining branches on updated main
5. Agents continue from the new base

### Branch Naming Convention

```
feat/[component]-[feature]     → New features
fix/[component]-[description]  → Bug fixes
test/[component]-[what]        → Test additions
refactor/[component]-[what]    → Refactors

Examples:
feat/backend-session-entries
feat/backend-session-plans
feat/mobile-session-timeline
feat/pipeline-per-clip-parser
feat/brain-rag-service
fix/parser-weight-normalization
test/parser-edge-cases
```

### Merge Rules

- Never merge directly to main without review
- All tests must pass on the branch before merge
- Squash merge for clean history (one commit per feature)
- Main branch must always be in a working state

---

## Feature Dependency Map (PRD v3)

```
Phase 1: Backend Foundation + Voice Pipeline (Weeks 1-4)
    ├── Models + Database (10 models, Alembic migration)
    │       ↓
    │       ├── Client CRUD
    │       ├── Session CRUD (with scheduled_for)
    │       ├── Session Entry CRUD (exercise_card + observation_card)
    │       ├── Session Plan CRUD
    │       └── Injury Flag CRUD
    │               ↓
    │               └── Voice Pipeline (Deepgram STT + Claude Parser)
    │                       ├── Per-clip synchronous processing (≤3s)
    │                       ├── Session state management (client-side)
    │                       └── Intent classification + additive parsing
    │
Phase 2: Mobile App — Core Session Flow (Weeks 5-7)
    │       ├── Navigation shell (Home, Clients, Brain, Session tabs)
    │       ├── Session screen with real-time timeline
    │       ├── Tap-to-speak recording flow
    │       ├── Client profile + session history
    │       └── Onboarding flow
    │
Phase 3: Pre-Session Context + The Brain (Weeks 8-12)
    │       ├── Planning flow (voice → structured exercise cards)
    │       ├── 4-layer pre-session briefing
    │       ├── Push notifications (Expo)
    │       └── The Brain (RAG + conversational agent)
    │               ├── Single-client + cross-client queries
    │               ├── Three honest states
    │               ├── Plan creation/modification via voice
    │               └── Conversation history (threads)
    │
Phase 4: Calendar + Auth + Launch Prep (Weeks 13-16)
    │       ├── Google Calendar + Apple Calendar integration
    │       ├── Supabase Auth (email + OAuth)
    │       └── Settings, polish, beta launch
    │
Phase 5: Intelligence Layer (Weeks 17-20)
    │       ├── Client score algorithm (green/yellow/red)
    │       ├── Pattern detection engine
    │       ├── Injury risk scoring
    │       └── Progress charts
    │
Phase 6: Growth Features (Weeks 21-24+)
            ├── Client app + wearable integration
            ├── Multi-trainer + session sharing
            └── Client Health Profile
```

**What can be parallelized:**
- Backend CRUD endpoints (clients, sessions, entries, plans, injuries — all independent)
- Backend CRUD + Mobile app scaffolding (different agents, same phase)
- Voice pipeline services (Deepgram + Claude parser + exercise DB — independent)
- Pattern detection algorithms (weight, pain, form, volume — independent)
- Brain service + Briefing service (both depend on data, independent of each other)

---

## When Worktrees Are Most Valuable

**High parallelization phases:**
- Phase 1, Week 1-2: 4 endpoint groups built simultaneously (clients, sessions, entries, plans)
- Phase 1, Week 3-4: Deepgram + Claude parser + exercise DB + validation — all independent
- Phase 2, Week 5-6: Mobile screens built in parallel (no shared state yet)
- Phase 5: Pattern detection algorithms (weight, pain, form, volume — all independent)

**Low parallelization phases:**
- Phase 2, Week 7: Session detail + polish (sequential refinement)
- Phase 4, Week 14: Auth touches every endpoint (harder to split)

---

## Task Tracking

I maintain `tasks/todo.md` with checkboxes for the current phase. Updated in real-time as I work.

```
Example (Phase 1, Week 3-4):

## Week 3-4: Voice Pipeline

### Deepgram Integration
- [x] Create Deepgram service class
- [x] Implement per-clip audio → transcript
- [x] Add keyterm prompting config
- [ ] Test with noisy audio sample
- [ ] Handle API errors and retries

### Claude Parser
- [x] Design tool_use schema for structured output
- [ ] Write parsing prompt v1
- [ ] Implement session state management
- [ ] Test on 5 sample transcripts
- [ ] Iterate on prompt based on failures
```

---

## Communication Protocol

**When I need a decision from you:**
I'll ask clearly with options and my recommendation. Example:
> "The parser needs to handle session state across clips. Should we maintain state client-side (sent with each clip request) or server-side (stored in memory/redis)? I recommend client-side (stateless server, simpler). Option A: client-side state. Option B: server-side state."

**When something is blocked:**
I'll tell you immediately, not bury it in a status update. Example:
> "I can't test the Deepgram integration without an API key. Can you sign up at deepgram.com and paste the key?"

**When something went wrong:**
I'll tell you what happened, why, and what I'm doing about it. No hiding failures. Example:
> "The Claude parser is only 70% accurate on your sample transcripts. The main failure mode is additive parsing ('oh, 80 kilos I forgot' not attaching to previous entry). I'm rewriting the prompt to handle this. ETA: 2 hours."
