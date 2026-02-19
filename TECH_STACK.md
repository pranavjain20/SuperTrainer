# SuperTrainer: Tech Stack Decisions

Each choice below includes what we're using, why, what we considered, and why we rejected the alternatives.

---

## 1. Speech-to-Text: Deepgram Nova-3

**What it does:** Converts trainer's voice recording into text transcript.

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
- Monthly audio: 100 × 30 × 4 × 10 = 120,000 minutes
- Deepgram batch: 120,000 × $0.0043 = ~$516/month

---

## 2. AI/LLM: Anthropic Claude (Sonnet)

**What it does:** Parses transcripts into structured data. Generates pre-session briefings. Explains patterns.

**Why Claude Sonnet:**

- **tool_use for reliable JSON** — Claude's tool_use feature returns structured JSON matching a schema you define. No parsing free-text, no regex to extract JSON from markdown. This is critical for our parser — we need reliable structured output every time.
- **Best at structured extraction** — Claude consistently outperforms GPT-4o on complex structured extraction tasks in benchmarks and real-world usage.
- **Cost-effective** — Sonnet is ~$3/million input tokens, $15/million output tokens. A 10-minute transcript (~2000 tokens) + our parsing prompt (~500 tokens) + structured output (~800 tokens) costs roughly $0.015 per session.
- **You already know the ecosystem** — Claude Pro Max subscriber, familiar with the SDK.

**Alternatives considered:**

- **OpenAI GPT-4o** — Comparable quality, function calling works similarly. Slightly more expensive. No strong reason to switch since you're already in the Claude ecosystem.

- **Open source (Llama, Mistral)** — Free inference but: need GPU hosting ($50-200/month for a single GPU server), worse at structured extraction, more hallucination on complex prompts. The hosting cost alone exceeds Claude API costs at our scale.

- **Claude Haiku** — Cheaper (~$0.25/million input, $1.25/million output) but significantly less capable at complex extraction. Risk of lower parser accuracy. Not worth the savings.

**Cost at scale (100 trainers, 120 sessions/week):**
- Parsing: 120 × 4 × $0.015 = ~$29/month
- Briefings: 120 × 4 × $0.01 = ~$19/month
- Pattern explanations: ~$10/month
- Total: ~$60-80/month (this is very cheap relative to value)

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

**What it does:** Stores all structured data — clients, sessions, exercises, injury flags, analysis.

**Why PostgreSQL:**

- **JSONB** — We store sets data as JSON arrays (`[{set: 1, weight: 135, reps: 10}, ...]`). PostgreSQL's JSONB lets us query inside JSON fields efficiently. "Find all sessions where any set exceeded 200lbs" is a single query.
- **Industry standard** — Most deployed relational database for SaaS. Every ORM supports it. Every hosting platform offers it managed.
- **SQLAlchemy 2.0** — Best Python ORM, excellent PostgreSQL support, async-capable. Alembic for migrations.

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

**What it does:** Processes audio files asynchronously. Trainer uploads audio, gets immediate response, processing happens in background.

**Why ARQ:**

- **Native asyncio** — Perfect fit for FastAPI. Task functions use `await` — same as your API code. No impedance mismatch. Your Deepgram API calls, Claude API calls, and database writes are all async.
- **Lightweight** — ~30MB per worker vs Celery's ~100MB. On a $5/month Railway plan, RAM matters.
- **Simple API** — `await redis.enqueue_job('process_audio', session_id=123)`. That's it.
- **Built-in retries and scheduling** — retry on failure, schedule tasks for later.
- **Our workload is I/O-bound** — We're calling Deepgram and Claude APIs, not crunching numbers. Async handles this efficiently in a single worker process.

**Alternatives considered:**

- **Celery + Redis** — Battle-tested at Instagram scale. But: synchronous by default (prefork workers, not asyncio). Running async code in Celery requires workarounds. Heavy memory footprint. Hundreds of configuration options. Overkill for <100 tasks/day.

- **FastAPI BackgroundTasks** — Zero setup. But: runs in your API process. A 30-second audio processing task blocks event loop resources and degrades API responsiveness. No persistence — server crash = lost tasks. No retries, no status tracking.

- **Dramatiq** — Simpler than Celery, good defaults. But: synchronous workers (same async mismatch as Celery).

**ARQ risk:** Maintenance-only mode (original author not adding features). The library is stable and production-ready, but if a critical bug is found, community fixes may be slow. Acceptable risk for now — we can migrate to Celery or a maintained fork if this becomes a problem.

---

## 6. Mobile: React Native + Expo

**What it does:** Cross-platform mobile app (iOS + Android) for voice recording, client management, session review, briefings.

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

**Alternatives considered:**

- **Auth0** — Powerful but $23/month for 1,000 users. Too expensive pre-revenue.
- **Clerk** — Modern DX, $25/month. Same problem.
- **Firebase Auth** — Free and solid. But: ties you to Google ecosystem. Supabase is more portable.
- **Custom auth** — Never. You will get it wrong. Use a service.

**Note:** We're using Supabase only for auth (and possibly file storage later), not as our primary database. The database lives on Railway.

---

## 8. File Storage: Supabase Storage (free tier)

**What it does:** Stores audio files uploaded by trainers.

**Why Supabase Storage:**

- **Free tier: 1GB** — Enough for early development and first users.
- **S3-compatible API** — presigned URLs for upload/download, same patterns as AWS S3.
- **Integrated with Supabase Auth** — Row-level security on files (trainer can only access their clients' audio).
- **Already using Supabase for auth** — No new vendor.

**Alternatives considered:**

- **AWS S3** — More features, cheaper at massive scale. But: separate service to manage, more config, and we're not at the scale where S3 pricing matters.
- **Cloudflare R2** — No egress fees, cheap. Good option if Supabase storage becomes limiting. Easy migration since both are S3-compatible.

---

## Full Stack Summary

- **Mobile:** React Native + Expo (TypeScript)
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL on Railway
- **Task Queue:** ARQ + Redis on Railway
- **Auth:** Supabase Auth (free)
- **File Storage:** Supabase Storage (free)
- **STT:** Deepgram Nova-3
- **LLM:** Anthropic Claude Sonnet (tool_use)
- **Hosting:** Railway ($5-20/month)

**Monthly cost pre-revenue: ~$15-25/month**
(Railway Hobby $5 + Redis $3-5 + Deepgram free credits + Claude API ~$5-10 during dev)

**Monthly cost at 100 paying users:**
- Railway: $20-40
- Deepgram: $500-600
- Claude API: $60-80
- Supabase: $0-25
- Total: ~$600-750/month
- Revenue at $199/user: $19,900/month
- Gross margin: ~96%
