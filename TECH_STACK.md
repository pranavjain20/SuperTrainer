# SuperTrainer: Tech Stack Decisions

Each choice below includes what we're using, why, what we considered, and why we rejected the alternatives.

---

## 1. Speech-to-Text: Deepgram Nova-3

**What it does:** Converts trainer's voice recordings into text transcripts. Each voice clip (typically 5-30 seconds) is transcribed individually as part of the per-clip session flow.

**Why Deepgram:**

- **Keyterm Prompting** — You can inject up to 100 custom terms at inference time ("Romanian deadlift", "RPE", "superset", "barbell hip thrust") with no model retraining. This is a game-changer for gym vocabulary. Up to 6x recall improvement on domain terms. No other provider offers this at base price.
- **Built for noisy audio** — Nova-3 was designed for far-field, noisy environments (drive-thrus, call centers, body cams). Gyms are analogous.
- **$200 free credits** — That's ~433 hours of audio. Months of development runway without spending a dollar.
- **Streaming support** — Can show real-time transcript as trainer speaks.
- **Per-second billing** — 7 minutes of audio costs exactly 7 minutes. No rounding.
- **Batch pricing: $0.0043/min ($0.26/hr)** — Cheapest among top-tier providers for pre-recorded audio.

**Alternatives considered:**

- **ElevenLabs Scribe** — Claims 96.7% accuracy (highest benchmark). But: no custom vocabulary/keyterm prompting (critical for exercise names), relatively new in STT (launched Feb 2025, less battle-tested), and no clear accuracy advantage in noisy environments. Good product, but Deepgram's keyterm feature is more valuable for our use case than slightly higher benchmark accuracy.

- **OpenAI Whisper / GPT-4o Transcribe** — GPT-4o Mini Transcribe is cheapest at $0.003/min. But: no streaming (batch only), no custom vocabulary, and Whisper has a known hallucination problem (generates plausible but fabricated text during silence or noise). In a gym with pauses between exercises, this is a real risk. Bills for silence too.

- **AssemblyAI** — Cheapest streaming at $0.15/hr with generous free tier (333 hours). But: keyterm prompting is an add-on ($0.04/hr extra), and add-on pricing stacks up. Good runner-up.

- **Google Cloud Speech-to-Text** — 2-6x more expensive than every competitor ($0.96-2.16/hr). Worst accuracy in independent benchmarks. No advantage for our use case.

**ElevenLabs note:** We may still use ElevenLabs for text-to-speech later (reading briefings aloud). Their STT isn't the right fit, but their TTS is best-in-class.

**Cost at scale (100 trainers, 30 sessions/week each, avg 10 min/session):**
- Monthly audio: 100 x 30 x 4 x 10 = 120,000 minutes
- Deepgram batch: 120,000 x $0.0043 = ~$516/month

---

## 2. AI/LLM: Anthropic Claude (Sonnet)

**What it does:** Three roles in the product:
1. **Transcript parsing** — Takes each voice clip's transcript plus full session context so far, returns structured JSON (exercise cards, observation cards, set data, flags) via tool_use.
2. **Briefing generation** — Generates the four-layer pre-session briefing based on retrieved client data and data maturity rules.
3. **The Brain** — Conversational agent that answers questions, reasons across client data, and takes actions (plan creation/modification) using RAG over the trainer's data.

**Why Claude Sonnet:**

- **tool_use for reliable JSON** — Claude's tool_use feature returns structured JSON matching a schema you define. No parsing free-text, no regex to extract JSON from markdown. This is critical for our parser — we need reliable structured output every time.
- **Best at structured extraction** — Claude consistently outperforms GPT-4o on complex structured extraction tasks in benchmarks and real-world usage.
- **Cost-effective** — Sonnet is ~$3/million input tokens, $15/million output tokens. A 10-minute transcript (~2000 tokens) + our parsing prompt (~500 tokens) + structured output (~800 tokens) costs roughly $0.015 per session.
- **You already know the ecosystem** — Claude Pro Max subscriber, familiar with the SDK.

**RAG approach for the Brain — hybrid retrieval from day one:**

The Brain uses two retrieval mechanisms working together:

1. **Structured SQL queries** — For precise, structured data. "What weight was Pranav using for squats last time?" constructs a targeted SQL query against sessions, session_entries, and related tables. SQL is precise, fast, and predictable for structured data (exercises, sets, reps, weights, dates, pain flags).

2. **Semantic search via pgvector** — For fuzzy, meaning-based queries. "Which clients have been struggling with motivation?" or "Has anyone mentioned feeling burnt out?" can't be answered with SQL alone. We generate embeddings for text-heavy fields (observation_text, form_notes, plan_text, raw_transcript) and store them via pgvector. The Brain searches by meaning, not just keywords.

**Why both from day one:** If we only add embeddings later, we'd need to backfill all historical sessions. By generating embeddings from the first session saved in Phase 1, The Brain has a rich semantic index ready when it launches in Phase 3. The cost is negligible (OpenAI `text-embedding-3-small` at $0.02/million tokens) and the setup is minimal (pgvector is a PostgreSQL extension — one line in the migration).

**How hybrid retrieval works:** When the trainer asks a question, the system decides which retrieval to use (or both). Structured questions → SQL. Semantic questions → vector similarity. Ambiguous questions → both, results merged and ranked before passing to Claude as context.

**Three honest states enforcement:** The system prompt explicitly instructs the Brain to identify which state it is in for each answer:
1. Full answer — has both domain knowledge and client-specific data
2. Partial answer — has knowledge but insufficient client data
3. Neither — offers to look it up (see Tavily in section 10)

**Alternatives considered:**

- **OpenAI GPT-4o** — Comparable quality, function calling works similarly. Slightly more expensive. No strong reason to switch since you're already in the Claude ecosystem.

- **Open source (Llama, Mistral)** — Free inference but: need GPU hosting ($50-200/month for a single GPU server), worse at structured extraction, more hallucination on complex prompts. The hosting cost alone exceeds Claude API costs at our scale.

- **Claude Haiku** — Cheaper (~$0.25/million input, $1.25/million output) but significantly less capable at complex extraction. Risk of lower parser accuracy. Not worth the savings.

**Cost at scale (100 trainers, 120 sessions/week):**
- Parsing: 120 x 4 x $0.015 = ~$29/month
- Briefings: 120 x 4 x $0.01 = ~$19/month
- Brain queries + pattern explanations: ~$20/month
- Total: ~$70-90/month (this is very cheap relative to value)

---

## 3. Backend: Python 3.12 + FastAPI

**What it does:** API server handling all requests, business logic, and orchestration.

**Why FastAPI:**

- **Native async** — Audio processing, STT calls, and LLM calls are all I/O-bound. FastAPI's async/await handles concurrent requests efficiently without threading complexity.
- **Automatic API docs** — Swagger UI generated from your code. Free interactive API documentation for testing and debugging.
- **Pydantic integration** — Request/response validation with type hints. Catches bugs at the boundary, not deep in business logic.
- **Python = AI ecosystem** — Claude SDK, data processing (pandas, numpy), ML libraries (scikit-learn) — all Python. No language boundary.
- **Your strongest language** — MS Data Science at Columbia. Python is what you know best.

**Alternatives considered:**

- **Django + DRF** — More batteries-included (admin panel, ORM, auth). But: heavier, slower startup, worse async support, more boilerplate for API-only apps. Django's admin panel is nice but we don't need it — our UI is the mobile app. The ORM (Django ORM) is less flexible than SQLAlchemy for complex queries.

- **Node.js (Express/Fastify)** — Would match frontend language (TypeScript). But: you'd lose the entire Python AI ecosystem. The Claude SDK, data processing, and eventual ML work all become harder. Not worth the language consistency.

- **Go / Rust** — Better raw performance. But: we're I/O-bound (waiting on APIs), not CPU-bound. The performance difference is irrelevant. Development speed matters more.

---

## 4. Database: PostgreSQL (on Railway)

**What it does:** Stores all structured data — trainers, clients, sessions, session entries, injury flags, client analysis, brain conversations, plans.

**Why PostgreSQL:**

- **JSONB** — We store sets data as JSON arrays (`[{set: 1, weight: 135, reps: 10}, ...]`). PostgreSQL's JSONB lets us query inside JSON fields efficiently. "Find all sessions where any set exceeded 200lbs" is a single query.
- **Industry standard** — Most deployed relational database for SaaS. Every ORM supports it. Every hosting platform offers it managed.
- **SQLAlchemy 2.0** — Best Python ORM, excellent PostgreSQL support, async-capable. Alembic for migrations.
- **pgvector extension** — Enables semantic search via embeddings in the same PostgreSQL instance. No separate vector database needed. Set up in Phase 1, used by The Brain in Phase 3 for hybrid retrieval (SQL + semantic search).

**Why Railway (not Supabase) for the database:**

- Railway gives us database + API hosting on one platform. One dashboard, one deploy pipeline.
- Supabase's free tier pauses after 7 days of inactivity — unacceptable for production.
- Supabase Pro ($25/month) is fine, but Railway's included PostgreSQL at $5/month (Hobby) is cheaper and simpler when we're already hosting our API there.
- We can migrate to Supabase or AWS RDS later if needed. SQLAlchemy makes the switch painless.

**Alternatives considered:**

- **MySQL** — Weaker JSON support. No strong advantage over Postgres for our use case.
- **MongoDB** — Document store fits session data well, but we lose relational integrity for trainer-client relationships. Complex queries for pattern detection (joins across sessions, exercises, injury flags) are painful in MongoDB.
- **SQLite** — Great for local dev, but can't handle concurrent writes from API + background workers. Not suitable for production.

---

## 5. Task Queue: ARQ + Redis

**What it does:** Handles background jobs that should not block API responses.

**Important clarification on what is and is not async:**

Per-clip voice processing is synchronous — it runs in the request path. A single voice clip (5-30 seconds of audio) takes roughly 1-3 seconds total to transcribe via Deepgram and parse via Claude. This is fast enough to return in the HTTP response, and the real-time session timeline requires it. There is no benefit to making per-clip processing async — the trainer needs the result immediately to see their timeline update.

**ARQ handles truly async workloads:**
- **Briefing generation** — Generating the four-layer pre-session briefing involves multiple database queries and an LLM call. Triggered by notification scheduling, not by a trainer waiting for a response.
- **Client analysis recomputation** — After a session is saved, the `client_analysis` table is recomputed: injury risk score, progression trends, client score, overtraining indicators. This can take several seconds and does not need to block the session save.
- **Notification scheduling** — Scheduling and dispatching push notifications (briefing notifications 10-15 minutes before sessions) is a background job.
- **Future background jobs** — Exercise database updates, batch analytics, data exports, anything that does not need an immediate response.

**Why ARQ:**

- **Native asyncio** — Perfect fit for FastAPI. Task functions use `await` — same as your API code. No impedance mismatch. Deepgram API calls, Claude API calls, and database writes are all async.
- **Lightweight** — ~30MB per worker vs Celery's ~100MB. On a $5/month Railway plan, RAM matters.
- **Simple API** — `await redis.enqueue_job('generate_briefing', client_id=123)`. That's it.
- **Built-in retries and scheduling** — Retry on failure, schedule tasks for later (e.g., schedule a briefing generation job 20 minutes before a session).
- **Our workload is I/O-bound** — We're calling APIs, not crunching numbers. Async handles this efficiently in a single worker process.

**Alternatives considered:**

- **Celery + Redis** — Battle-tested at Instagram scale. But: synchronous by default (prefork workers, not asyncio). Running async code in Celery requires workarounds. Heavy memory footprint. Hundreds of configuration options. Overkill for our workload.

- **FastAPI BackgroundTasks** — Zero setup. But: runs in your API process. No persistence — server crash = lost tasks. No retries, no status tracking. Not suitable for briefing generation or analysis recomputation where reliability matters.

- **Dramatiq** — Simpler than Celery, good defaults. But: synchronous workers (same async mismatch as Celery).

**ARQ risk:** Maintenance-only mode (original author not adding features). The library is stable and production-ready, but if a critical bug is found, community fixes may be slow. Acceptable risk for now — we can migrate to Celery or a maintained fork if this becomes a problem.

---

## 6. Mobile: React Native + Expo

**What it does:** Cross-platform mobile app (iOS + Android) for voice recording, session management, client profiles, the Brain, and briefings.

**Why React Native + Expo:**

- **Cross-platform from day one** — One codebase, both platforms. As a solo dev, you cannot maintain two native codebases.
- **Expo simplifies everything** — OTA updates (push fixes without App Store review), push notifications (Expo Push), build service (EAS Build), audio recording (expo-av).
- **expo-av** — Proven audio recording library. Handles background recording, audio format configuration, and playback. This is our core mobile feature.
- **Large ecosystem** — More third-party packages than Flutter. Most React libraries have React Native equivalents.
- **TypeScript** — Type safety on the frontend. Catches API contract mismatches early.

**Alternatives considered:**

- **Flutter** — Better raw performance, hot reload is excellent. But: Dart is a language you'd have to learn. Smaller package ecosystem. Audio recording packages are less mature than expo-av. The performance advantage is irrelevant — our app is forms and lists, not graphics-intensive.

- **Native (Swift + Kotlin)** — Best performance and platform integration. But: double the development effort. As a solo dev, this is a non-starter. You'd spend half your time on platform-specific code instead of product features.

- **Web app (React + Vite)** — Fastest to build. But: no push notifications (not reliable on mobile browsers), no offline support (ServiceWorker is limited), audio recording is less reliable across browsers, and "install from App Store" is a trust signal for paying customers. A web app feels like a side project. A mobile app feels like a product.

---

## 7. Auth: Supabase Auth (free tier)

**What it does:** User registration, login, OAuth (Google, Apple), JWT tokens, password reset.

**Why Supabase Auth:**

- **Free for 50K monthly active users** — We won't hit this for years.
- **OAuth built-in** — Google and Apple sign-in with minimal config.
- **JWT tokens** — Standard, works with FastAPI middleware.
- **You don't build auth yourself** — Auth is a solved problem. Rolling your own is a security risk and a waste of time.

**How it integrates with our data model:**

Supabase handles ALL credential storage and authentication. Our `trainers` table does not have a `password_hash` column — Supabase owns that entirely. In Phase 4 (Auth + Security), we add a `supabase_user_id` column to the `trainers` table to link our trainer record to the Supabase user.

During development (Phases 1-3), we use a temporary trainer ID pattern — a hardcoded first trainer for all API calls. This avoids building auth infrastructure before we need it while keeping the data model clean. The transition to real auth in Phase 4 is a single migration adding the `supabase_user_id` FK and middleware to validate JWTs.

**Alternatives considered:**

- **Auth0** — Powerful but $23/month for 1,000 users. Too expensive pre-revenue.
- **Clerk** — Modern DX, $25/month. Same problem.
- **Firebase Auth** — Free and solid. But: ties you to Google ecosystem. Supabase is more portable.
- **Custom auth** — Never. You will get it wrong. Use a service.

**Note:** We're using Supabase only for auth (and file storage), not as our primary database. The database lives on Railway.

---

## 8. File Storage: Supabase Storage (free tier)

**What it does:** Stores audio files uploaded by trainers.

**Why Supabase Storage:**

- **Free tier: 1GB** — Enough for early development and first users.
- **S3-compatible API** — Presigned URLs for upload/download, same patterns as AWS S3.
- **Integrated with Supabase Auth** — Row-level security on files (trainer can only access their clients' audio).
- **Already using Supabase for auth** — No new vendor.

**Alternatives considered:**

- **AWS S3** — More features, cheaper at massive scale. But: separate service to manage, more config, and we're not at the scale where S3 pricing matters.
- **Cloudflare R2** — No egress fees, cheap. Good option if Supabase storage becomes limiting. Easy migration since both are S3-compatible.

---

## 9. Push Notifications: Expo Push Notifications

**What it does:** Sends push notifications to the trainer's phone. Primary use case: the pre-session briefing notification that fires 10-15 minutes before a scheduled session.

**Why Expo Push:**

- **Already using Expo** — Expo Push is built into the Expo ecosystem. No additional SDK, no separate service, no extra vendor. `expo-notifications` handles token management, permissions, and delivery.
- **Free tier is generous** — No per-message cost. Expo handles delivery to both APNs (Apple) and FCM (Google) behind a single unified API.
- **Simple server-side** — Send a POST request to `https://exp.host/--/api/v2/push/send` with the push token and message. ARQ schedules the job, the job sends the request. Done.
- **Receipt tracking** — Expo provides delivery receipts so we can detect failed deliveries and retry.

**How it works in our architecture:**

1. Mobile app registers for push notifications on first launch, gets an Expo push token.
2. Token stored in the backend (on the trainer record).
3. When a session is detected from calendar (or manually created with a scheduled time), ARQ schedules a background job for [session_time - 15 minutes].
4. The job generates the briefing (four-layer structure from Feature 2), then sends a push notification with the client name and one-line preview of the most important flag.
5. Trainer taps notification, opens the full briefing, which opens the Brain with briefing context pre-loaded.

**Alternatives considered:**

- **Firebase Cloud Messaging (FCM) directly** — More control, but requires managing APNs certificates separately for iOS. Expo abstracts this. Not worth the additional complexity.
- **OneSignal** — Feature-rich (segments, A/B testing, analytics). But: overkill for our use case. We are sending targeted notifications to specific trainers at specific times, not broadcasting to segments. Free tier is fine but adds an unnecessary vendor.
- **AWS SNS** — Enterprise-grade, complex setup. No advantage for a solo-dev mobile app already on Expo.

**Cost at scale:** Free. Expo Push does not charge per message. The only cost is the Expo infrastructure we're already using.

---

## 10. Web Search: Tavily API (Phase 3+)

**What it does:** Provides web search capability for the Brain's State 3 — when it doesn't have sufficient knowledge or client data to answer a question accurately, it offers to look it up.

**Why Tavily:**

- **Built for AI agents** — Returns clean, structured results optimized for LLM consumption. Not raw HTML. Not ten blue links. Extracted, relevant content ready to pass into Claude's context.
- **Simple API** — One endpoint, one API key. `POST /search` with a query, get back structured results. No OAuth, no complex setup.
- **Generous free tier** — 1,000 searches/month free. More than enough for development and early users (State 3 queries are uncommon by design — the Brain should know most things).
- **Fast** — Sub-second response times. Combined with Claude's processing, the full State 3 flow (search + synthesize answer) stays under 5 seconds.

**When it gets used:**

State 3 is the least common state. Most questions fall into State 1 (have knowledge + data) or State 2 (have knowledge, need more data). State 3 fires for things genuinely outside Claude's training — highly specific medical questions, rare conditions, niche exercise variations, recent research. The Brain says "I don't have enough information to answer that accurately. Want me to look it up?" — trainer says yes — Tavily searches — Claude synthesizes the results into an answer.

This is a Phase 3+ addition. The Brain ships in Phase 3 with States 1 and 2 fully working. State 3 with web search is added once the core Brain is stable.

**Alternatives considered:**

- **Google Custom Search API** — $5 per 1,000 queries after 100 free. Returns raw search results, not agent-optimized content. Requires more post-processing.
- **Bing Web Search API** — Similar to Google. Returns HTML-heavy results not optimized for LLM consumption.
- **Perplexity API** — Strong AI-powered search. But: more expensive ($5/1,000 queries on pro), and we're already using Claude for synthesis — we just need the search results, not another LLM layer.
- **SerpAPI** — Good for scraping Google results. But: $50/month minimum for meaningful usage. Overkill for an uncommon code path.

**Cost at scale (100 trainers):**
- Estimated State 3 queries: 2-5 per trainer per month = 200-500 searches/month
- Free tier covers this. Paid tier ($20/month for 5,000 searches) if usage grows.

---

## 11. Calendar Integration: Google Calendar API + Apple CalDAV (Phase 4)

**What it does:** Connects the trainer's calendar to SuperTrainer. Sessions already in the trainer's calendar automatically appear in the app, trigger briefing notifications, and reduce manual session creation to zero.

**Why these two:**

- **Google Calendar** — The majority of trainers use Google Calendar or Outlook. Google Calendar API is well-documented, OAuth 2.0 based, and has webhooks for real-time event updates (push notifications when calendar changes).
- **Apple Calendar (CalDAV)** — For trainers on iPhone who use Apple's built-in calendar. CalDAV is an open protocol, supported by Apple Calendar. More complex to implement than Google's API but covers the Apple-native users.

**How it works in our architecture:**

1. Trainer connects their calendar in Settings (OAuth flow for Google, CalDAV auth for Apple).
2. Backend polls or receives webhooks for upcoming events.
3. Trainer does a one-time mapping: calendar contacts to app clients ("John Smith in calendar = John S. in SuperTrainer"). Automatic matching by name thereafter.
4. When a session is detected from calendar, a session record is created in the app and a briefing notification is scheduled via ARQ for [session_time - 15 minutes].

**This is Phase 4 (Week 13).** Phases 1-3 use manually created sessions. The architecture supports adding calendar integration without restructuring — sessions already have a `started_at` field and the notification system is built in Phase 3.

**Alternatives considered:**

- **Calendly API** — Some trainers use Calendly for booking. But: Calendly is a booking tool, not a personal calendar. Most trainers still have the session on their personal calendar even if booked through Calendly.
- **Microsoft Graph API (Outlook)** — Would cover Outlook users. Can be added later if demand exists. Same OAuth pattern as Google.
- **Building our own scheduler** — Would mean asking trainers to enter their schedule in a new place. Trainers already have a calendar system that works. Integrating with it is always better than replacing it.

---

## 12. Hosting: Railway

**What it does:** Hosts the backend API, PostgreSQL database, Redis instance, and ARQ worker.

**Why Railway:**

- **Everything in one place** — API, database, Redis, worker. One dashboard, one deploy pipeline, one billing account.
- **$5/month Hobby plan** — Includes enough resources for development and early users.
- **Simple deploys** — Connect to GitHub, deploy on push. No Docker/Kubernetes configuration needed.
- **Scales when needed** — Can upgrade to Pro ($20/month) for more resources, or move individual services to dedicated infrastructure if a component becomes a bottleneck.

**Alternatives considered:**

- **Render** — Similar to Railway, good free tier. But: free tier sleeps after 15 minutes of inactivity (unacceptable for an app that receives push notification responses). Paid tier ($7/month) is comparable.
- **Fly.io** — Better for edge deployment and low-latency. But: more complex setup (Dockerfile required), and we don't need edge deployment — all our users are in the US initially.
- **AWS (ECS/Lambda)** — Enterprise-grade, infinitely scalable. But: complex setup, requires DevOps knowledge, expensive floor. Overkill for this stage.
- **Heroku** — Good DX but more expensive than Railway for comparable resources after the free tier sunset.

---

## Full Stack Summary

- **Mobile:** React Native + Expo (TypeScript)
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL on Railway (pgvector from Phase 1 for semantic search)
- **ORM:** SQLAlchemy 2.0 (async) + Alembic
- **Task Queue:** ARQ + Redis on Railway
- **Auth:** Supabase Auth (free) — owns all credentials, no password_hash in our DB
- **File Storage:** Supabase Storage (free)
- **STT:** Deepgram Nova-3 (keyterm prompting for gym vocabulary)
- **LLM:** Anthropic Claude Sonnet (tool_use for parsing, hybrid RAG for the Brain)
- **Embeddings:** OpenAI text-embedding-3-small (for pgvector semantic search)
- **Push Notifications:** Expo Push Notifications
- **Web Search:** Tavily API (Brain State 3, Phase 3+)
- **Calendar:** Google Calendar API + Apple CalDAV (Phase 4)
- **Hosting:** Railway ($5-20/month)

**Monthly cost during development: ~$15-25/month**
(Railway Hobby $5 + Redis $3-5 + Deepgram free credits + Claude API ~$5-10 + OpenAI embeddings ~$0 during dev)

**Monthly infrastructure cost at 100 trainers:**
- Railway: $20-40
- Deepgram: $500-600
- Claude API: $70-90
- OpenAI embeddings: $1-5
- Supabase: $0-25
- Tavily: $0-20
- Expo Push: $0
- Total: ~$600-780/month
