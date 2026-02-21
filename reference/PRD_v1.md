# SuperTrainer — Product Requirements Document

**Version:** 1.0
**Date:** February 19, 2026
**Author:** Pranav Jain
**Status:** Pre-build

---

## Vision

AI coaching intelligence that gives personal trainers perfect memory and pattern recognition. Trainers record sessions via voice, AI structures the data, detects patterns, predicts risks, and generates briefings.

**One-liner:** "Intelligence infrastructure for professional coaches."

**This is NOT:** A workout logger. A scheduling tool. A CRM. Those exist. We are the intelligence layer that makes trainers better at their actual job — coaching.

---

## User

**Primary:** Independent personal trainers with 20-40 active clients.

They charge $60-80/session, see 8-10 clients/day, and cannot remember what happened 3 days ago with client #27. They currently use Notes app, Google Sheets, or nothing. They are not technical. They want something that works in 30 seconds, not 5 minutes.

---

## Core Loop

```
Trainer records session (voice)
    → AI transcribes
    → AI extracts structured data (exercises, sets, weights, observations, pain)
    → Trainer reviews + confirms (30 seconds)
    → Data saved to client history

Before next session:
    → AI generates briefing from history
    → AI flags patterns (progression, pain, form degradation)
    → AI scores injury risk
    → Trainer walks in prepared
```

---

## Features (Priority Ordered)

### Phase 1 — Core Voice Loop (Must work perfectly before anything else)

**F1: Voice Session Recording**
Mobile app. Trainer taps "Start Session" for a client, speaks during or after the session, taps "Stop." Audio captured and uploaded.

**F2: Speech-to-Text**
Audio sent to Deepgram Nova-3 API. Returns full transcript. Must handle gym noise (weights, music, multiple voices) at 90%+ accuracy on clear speech.

**F3: AI Session Parsing**
Claude API extracts structured data from transcript:
- Exercises performed (name, mapped to canonical)
- Sets, reps, weight per exercise
- Form observations
- Coaching cues given
- Client feedback / statements
- Pain and injury reports (body part, severity)
- Programming notes for next session

Uses Claude tool_use for reliable JSON. Hybrid approach: LLM extraction + rule-based validation for weight normalization, exercise name matching, implicit set expansion.

**F4: Session Review & Edit**
Trainer sees extracted data in clean UI. Can edit any field (exercise name, weight, reps, add/remove sets). Confirms to save. Edit rate tracked — target <20% sessions need editing.

**F5: Client Management**
Add/edit/archive clients. Client profile: name, contact, goals, injury history, training start date, notes.

**F6: Session History**
Chronological list of all sessions per client. Click to see full breakdown. Search across clients ("everyone with knee issues").

### Phase 2 — Intelligence Layer (What makes this worth paying for)

**F7: Pre-Session Briefing**
AI-generated briefing before each session. Last session recap, concerning patterns, risk alerts, cue reminders, suggested focus. Push notification before scheduled session.

**F8: Pattern Detection**
Rule-based engine detecting:
- Weight progression rate (too fast / stagnant / healthy)
- Pain frequency by body part (recurring = flag)
- Form quality degradation (increasing error rate)
- Volume and overtraining indicators
- Cue effectiveness (which cues improved form)

**F9: Injury Risk Scoring**
Score 0-100 with Low/Medium/High classification. Initially rule-based weighted formula. Migrate to ML (Random Forest) when sufficient real data exists (~6 months, 500+ clients). Explainable — shows top risk factors.

**F10: Trainer Dashboard**
All clients at a glance. Who's at risk, who's overdue, who's progressing. Quick-glance risk indicators. Notification center.

### Phase 3 — Growth Features (After product-market fit is proven)

**F11: Authentication & Multi-Trainer**
Proper auth (Supabase — email + OAuth). Multi-trainer support for gyms. Permission-based client access. Gym owner dashboard.

**F12: Progress Charts**
Visual graphs: weight progression per exercise, volume trends, pain frequency timeline, risk score history. Exportable.

**F13: Session Sharing**
Send session summary to client via email/SMS. Clean branded format.

**F14: Billing**
Stripe subscriptions. Free tier (5 clients, 10 sessions/month). Pro tier ($199/month, unlimited). Gym tier ($499/month, multiple trainers).

**F15: Offline Support**
Record audio offline, queue for upload. Local cache for client data. Background sync.

### Phase 4 — Moat Features (Competitive advantage)

**F16: ML Injury Prediction**
Trained model replacing rule-based scoring. Retrained monthly on real data. Validated against actual injury outcomes.

**F17: Exercise Database**
500+ exercises with aliases, muscle groups, equipment, common errors, coaching cues. Community contributions.

**F18: Wearable Integration**
Whoop, Oura, Apple Watch data. Sleep, HRV, readiness scores feed into risk model.

**F19: Client Portal**
Clients see their own training data. Progress charts. Trainer's notes (selectively shared).

---

## Technical Architecture

See `TECH_STACK.md` for full analysis with alternatives and rationale for each choice.

**Summary:**
- **Mobile:** React Native + Expo (TypeScript)
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL on Railway
- **Task Queue:** ARQ + Redis on Railway
- **Auth:** Supabase Auth (free tier)
- **File Storage:** Supabase Storage (free tier)
- **STT:** Deepgram Nova-3 (keyterm prompting for gym vocabulary)
- **LLM:** Anthropic Claude Sonnet (tool_use for reliable structured extraction)
- **Hosting:** Railway ($5-20/month)

### Data Model

**trainers** — id, email, password_hash, name, phone, tier, created_at, last_login

**clients** — id, trainer_id, name, email, phone, birth_date, training_start_date, goals[], injury_history, archived, created_at

**sessions** — id, trainer_id, client_id, started_at, ended_at, duration_minutes, audio_url, audio_duration_seconds, raw_transcript, processing_status, trainer_edited, created_at, updated_at

**exercise_logs** — id, session_id, client_id, exercise_name, exercise_canonical, sets (JSONB), total_volume_kg, form_notes[], cues_given[], cue_effectiveness (JSONB), performed_at, created_at

**injury_flags** — id, client_id, session_id, exercise_log_id, body_part, pain_level (1-10), description, first_occurrence, last_occurrence, occurrence_count, resolved, resolved_at, flagged_at

**client_analysis** — id, client_id, total_sessions, last_session_date, avg_weight_increase_pct_per_week, current_volume_trend, injury_risk_score, injury_risk_level, risk_factors[], form_degradation_detected, overtraining_indicators, pain_pattern_detected, last_computed_at

**exercises** — id, canonical_name, aliases[], category, primary_muscles[], equipment[], difficulty, common_errors (JSONB), created_at

### API Design

All endpoints under `/api/v1/`

Success: `{"data": ..., "meta": {...}}`
Error: `{"error": {"code": "...", "message": "..."}}`
Pagination: cursor-based `?cursor=...&limit=20`
Weights stored in kilograms internally. Display conversion based on user preference.

---

## Build Plan

### Assumptions
- Pranav: 3-4 hours/day for review, decisions, testing, and steering
- Claude Code: unlimited hours, 4 parallel agents — can build while Pranav is unavailable
- The bottleneck is review quality, not coding speed
- Timeline is driven by "done right," not "done fast" — extend if needed
- Bootstrapped: minimize costs until revenue
- TDD: tests first, implement until they pass

### Phase 1: Core Voice Loop (Weeks 1-6)

**Week 1-2: Backend Foundation**
- Project setup: FastAPI + SQLAlchemy + PostgreSQL (Supabase)
- All data models + Alembic migrations
- Seed script with realistic demo data (3 clients, 8 sessions each)
- Client CRUD endpoints (list, create, get, update, archive)
- Session CRUD endpoints (create, get, list by client, update)
- Full test suite for all endpoints
- Milestone: all CRUD tests pass, API serves seeded data

**Week 3-4: Voice Pipeline**
- Deepgram Nova-3 integration (audio upload → transcript)
- Claude parsing service (transcript → structured JSON via tool_use)
- Rule-based validation layer (exercise name matching, weight normalization)
- Exercise database (JSON seed with 100 common exercises + aliases)
- Audio upload endpoint (Supabase Storage)
- ARQ worker for async processing
- End-to-end pipeline: upload audio → get structured session data
- Parser test suite: 15+ real transcript samples, verify extraction accuracy
- Milestone: upload audio file, get back correctly parsed exercises at 85%+ accuracy

**Week 5-6: Mobile App (Core Flow)**
- React Native + Expo project setup
- Voice recording screen (expo-av)
- Client list screen
- Session recording flow: select client → record → stop → uploading → review
- Session review/edit screen (edit extracted data, confirm to save)
- Session history screen (per client)
- API client layer with error handling
- Milestone: record audio on phone → see structured session data → save

### Phase 2: Intelligence Layer (Weeks 7-10)

**Week 7-8: Briefings + Patterns**
- Pre-session briefing service (Claude generates from session history)
- Briefing endpoint + mobile screen
- Pattern detection engine:
  - Weight progression analysis
  - Pain frequency tracking
  - Form quality trending
- Client analysis table: recompute after each session
- Risk scoring (rule-based weighted formula)
- Tests for all pattern detection logic
- Milestone: open client → see AI briefing with pattern alerts and risk score

**Week 9-10: Dashboard + Polish**
- Trainer dashboard screen (all clients, risk indicators, overdue flags)
- Push notifications for briefings (Expo push)
- Loading states, error handling, edge cases throughout
- Performance optimization (query efficiency, caching hot data)
- Comprehensive test coverage review
- Milestone: app feels complete and professional for core use case

### Phase 3: Launch Prep (Weeks 11-14)

**Week 11: Auth + Security**
- Supabase Auth integration (email signup + Google OAuth)
- JWT handling in mobile app (secure storage)
- Trainer-scoped data access (trainer can only see their clients)
- Password reset flow
- Audit logging

**Week 12: Billing + Onboarding**
- Stripe integration (free trial → Pro subscription)
- Free tier limits (5 clients, 10 sessions/month)
- Onboarding flow (first-time user experience)
- Settings screen (units, notifications, account)

**Week 13: Beta Prep**
- App Store / Play Store build prep (Expo EAS)
- Marketing landing page
- Bug bash: fix everything found in self-testing
- Seed exercise database to 200+ exercises

**Week 14: Beta Launch**
- Deploy to production
- Onboard 5-10 beta trainers (personal network, gym contacts, Reddit)
- Collect feedback aggressively
- Monitor error rates, API costs, performance

### Phase 4: Iterate + Scale (Weeks 15-24)

**Week 15-18: Feedback-Driven Iteration**
- Fix top 10 issues from beta feedback
- Parser accuracy improvements (prompt iteration, more test cases)
- Session sharing (email summaries to clients)
- Progress charts
- Offline recording support

**Week 19-22: Growth Features**
- Multi-trainer / gym support
- Client portal (optional)
- ML injury prediction model (if sufficient data exists)
- Exercise database expansion + community contributions

**Week 23-24: Scale**
- Performance at 100+ trainers
- Advanced analytics
- Wearable integrations (if market demands it)
- Marketing + growth experiments

---

## Success Metrics

**Phase 1 complete (Week 6):**
- Record voice → get structured session data on phone
- 85%+ parser accuracy on test transcripts
- Full test suite passing

**Phase 2 complete (Week 10):**
- Pre-session briefings working
- Pattern detection flagging real patterns in test data
- App feels ready to show to a trainer

**Beta launch (Week 14):**
- 5-10 trainers using the app
- Trainers record 3+ sessions/week
- Parser accuracy 85%+ on real data
- <20% sessions need manual editing

**Product-market fit (Week 24):**
- 50+ paying trainers
- $10K+ MRR
- Churn <10%/month
- NPS > 40
- Trainers saying "I can't go back to how I did it before"

---

## Open Risks

1. **Gym noise kills STT accuracy** — Test early with real gym recordings. If <80% accuracy, investigate lapel mics or post-session recording workflow.

2. **Trainers won't record consistently** — The product only works with data. If adoption is <3 sessions/week, intelligence layer is useless. Mitigate with push notifications, streak tracking, showing clear value from recordings.

3. **Claude parsing degrades on edge cases** — Budget continuous prompt iteration time. Track parser accuracy as a metric. Build comprehensive test suite.

4. **Solo builder bottleneck** — You can build the product solo. You cannot do sales, support, marketing, and engineering solo at scale. Plan to hire or find a co-founder after product-market fit.
