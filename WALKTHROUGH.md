# Phase 1a Walkthrough — Understanding What You Built

This is a learning guide. Read it like a book, not like documentation. By the end, you should be able to explain every piece of the SuperTrainer backend to anyone — an investor, a technical interviewer, or yourself three months from now.

---

## The Big Picture

Before we get into any code, let's understand what SuperTrainer actually does at the data level.

A personal trainer walks into a gym. They have a client — let's call her Elena, 68 years old, been training for a few months. The trainer opens SuperTrainer, and before the session even starts, the app shows them a briefing: "Elena's been progressing well on leg press — went from 30kg to 55kg over 15 sessions. Her right hip has been flagged twice in the last month. Watch for pain today."

During the session, the trainer records voice clips. "Elena did 3 sets of leg press, 55 kilos, 10 reps each. Good form on set 1 and 2, slight hip shift on set 3. She mentioned mild discomfort in her right hip again."

The AI transcribes that, structures it into exercise cards and observation cards, and saves it. After the session, the trainer can look back at Elena's entire history, see patterns, and plan the next session.

**That's the product.** Phase 1a built the foundation that stores all of this data and lets you create, read, update, and delete it through an API. No voice, no AI yet — just the data backbone that everything else will plug into.

---

## How the Backend is Organized

Think of the backend like a restaurant.

- **The front door** is `main.py`. Every request that comes in goes through this door. It decides which section of the restaurant to send you to.
- **The waiters** are the **routers** (files in `api/`). They take your order (the HTTP request), check if you're allowed to be here, and pass your order to the kitchen.
- **The kitchen** is the **service layer** (files in `services/`). This is where the actual work happens — creating records, fetching data, updating things.
- **The pantry** is the **database**. The kitchen grabs ingredients (data) from here and puts finished dishes (new records) back.
- **The menu** is `schemas.py`. It defines exactly what you can order (request shapes) and what you'll get back (response shapes). If you order something that's not on the menu, you get rejected before the kitchen even sees it.
- **The pantry labels** are `models.py`. They define what's stored, how it's organized, and how things relate to each other.

Every request follows this flow:

```
Client sends HTTP request
    → main.py routes it to the right router
        → Router validates ownership ("is this your data?")
            → Router calls the service function
                → Service talks to the database
                → Service returns the result
            → Router formats the response
        → Response goes back to the client
```

This separation matters. If we ever need to change how we store data, we only touch the service and models. If we need to change validation rules, we only touch schemas. If we need to add a new endpoint, we add a route and maybe a service function. Nothing is tangled together.

---

## The Data Model — How Everything Connects

This is the heart of the system. If you understand these 10 models and how they relate, you understand the entire backend.

### The Ownership Chain

Everything starts with a **Trainer**. A trainer owns clients. Clients have sessions. Sessions have entries. This creates a chain:

```
Trainer
  └── Client (belongs to one trainer)
        ├── Session (belongs to one client, one trainer)
        │     ├── SessionEntry (belongs to one session)
        │     └── InjuryFlag (belongs to one session)
        ├── SessionPlan (belongs to one client, one trainer)
        └── ClientAnalysis (one per client)
```

This chain is how we enforce security. When you ask "show me entry X," we don't just fetch it — we trace the chain: entry → session → client → trainer. If the trainer at the end of that chain isn't you, you get a 404. Not a 403 ("forbidden"), a 404 ("not found"). This way, a malicious user can't even tell if an ID exists — they just get "not found" whether the entry doesn't exist or belongs to someone else.

### The 10 Models

Let me walk through each one, in the order they make sense:

**1. Trainer** — The user of our app. Has an email, name, phone, and a subscription tier (free, pro, trainer_pro). The `supabase_user_id` field is empty for now — that's where we'll link to real authentication in Phase 4. For now, we fake it by assuming there's one trainer.

**2. Client** — A person the trainer works with. Has basic info (name, email, phone, birth date), training context (start date, goals, injury history), and an `archived` flag. Archiving is a soft delete — the client's data is preserved, they just don't show up in the default list anymore. The trainer might want to bring them back someday.

**3. Session** — One training session. The trainer met the client, they worked out, it got recorded. A session has `started_at` and `ended_at` timestamps, optional audio (for when voice recording is built), a `processing_status` (pending → processing → completed → failed, for the voice pipeline), and a `raw_transcript` (what the AI heard). The `plan_id` links to a SessionPlan — but it's optional and nullable. More on why below.

**4. SessionEntry** — This is the most interesting model. It represents one "moment" in a session. But there are two kinds of moments:

- **Exercise cards**: "Elena did 3 sets of leg press at 55kg." These have fields like `exercise_name`, `sets` (a JSON array of set data — weight, reps, RPE), `form_notes`, `cues_given`, and `cue_effectiveness`.
- **Observation cards**: "Elena seemed tired today" or "Client mentioned hip discomfort." These have `observation_text`, an optional `flag_color` (red/yellow/green), and can be `attached_to_set` (e.g., "this observation is about set 3").

Both types live in the same table, distinguished by an `entry_type` field ("exercise_card" or "observation_card"). The `sequence_order` field tracks the timeline — entry 1 happened before entry 2 happened before entry 3.

Why one table instead of two? Because in the real product, the trainer's session is a timeline. Exercise, observation, exercise, observation — they interleave. Keeping them in one table with a sequence order makes it trivial to display them in order. Two tables would mean merging and sorting across tables, which is messy.

The trade-off: some fields are null depending on the type. An exercise card has null `observation_text`. An observation card has null `exercise_name` and `sets`. We enforce this in the schema validation — if you try to set `observation_text` on an exercise card, you get a 422 error. The database allows the nulls, but the API doesn't let you create invalid combinations.

**5. SessionPlan** — A trainer's plan for an upcoming session. "Tomorrow with Elena: 3x10 leg press at 55kg, 3x12 step-ups, 2x15 band pull-aparts." The `plan_text` is free-form text (for now — Phase 3 will add structured parsing). `planned_for_date` is optional — a plan might not have a specific date yet.

Here's a key design decision: **plans and sessions are independent**. A plan doesn't "become" a session. The trainer creates a plan, then later creates a session, and can optionally link them via the session's `plan_id`. But the session might go completely differently from the plan — that's fine. The plan stays as-is, the session records what actually happened. This lets us compare "what was planned" vs "what was done" in Phase 3's briefing engine.

Why not just put the plan text inside the session? Because plans are created before sessions exist. The trainer plans tomorrow's workout today. The session for tomorrow doesn't exist yet. And sometimes plans aren't attached to any specific session — they're just notes.

**6. InjuryFlag** — Tracks pain and injuries across sessions. Each flag has a `body_part`, `pain_level` (1-10), optional `description`, and tracking fields: `first_occurrence`, `last_occurrence`, `occurrence_count`. The `resolved` boolean and `resolved_at` timestamp let trainers mark injuries as healed.

An injury flag always belongs to a session (when was it observed?) and a client (who has the injury?). It can optionally link to a specific `session_entry_id` (which exercise triggered the pain?).

The validation here is interesting. If you set `resolved_at` without setting `resolved=true`, you get a 422. It makes no logical sense to have a resolution timestamp on an unresolved injury. We catch this in the Pydantic schema with a model validator.

**7. ClientAnalysis** — A computed summary of a client's progress. Total sessions, weight increase trends, injury risk score, volume trends, and a `client_score` (0-100). This is read-only from the API — it gets computed by the patterns engine in Phase 3. One analysis per client (enforced by a unique constraint on `client_id`).

**8. Exercise** — A reference table of canonical exercise names. "Barbell Back Squat" with aliases ["squat", "back squat", "BB squat"]. The voice parser will use this to match fuzzy exercise names from transcripts. We seeded 19 exercises to start. Has fields for `primary_muscles`, `equipment`, `difficulty`, and `common_errors` — all useful for the AI later.

**9. BrainConversation** and **10. BrainMessage** — The data model for "The Brain," our conversational AI agent. A trainer can ask questions like "What's Elena's squat progression over the last 3 months?" and get answers grounded in real data. Each conversation has messages (user and assistant roles), stored for history. These models exist in the schema but have no API endpoints yet — they'll be built in Phase 3.

### How Deletes Work (Cascading)

When you delete something, you need to think about what happens to its children. We made deliberate choices:

- **Delete a trainer** → all their clients, sessions, plans, conversations go too. (CASCADE)
- **Delete a client** → all their sessions, entries, plans, flags, analysis go too. (CASCADE)
- **Delete a session** → all its entries and flags go too. (CASCADE)
- **Delete a plan** → sessions that referenced it get their `plan_id` set to null. (SET NULL, not CASCADE — the session still happened, we just lost the link to the plan)
- **Delete an entry** → injury flags that referenced it get their `session_entry_id` set to null. (SET NULL — the injury still happened, we just lost the link to which exercise caused it)

Every one of these cascades has a test proving it works.

### Embedding Columns (pgvector)

You'll notice some models have columns like `transcript_embedding`, `observation_embedding`, `form_notes_embedding`, `plan_text_embedding`. These are `Vector(1536)` columns — they store numerical representations of text (embeddings) that allow semantic search.

Right now they're empty. In Phase 3, when a trainer saves "good depth on squats, slight knee cave on set 3," we'll compute an embedding (a list of 1536 numbers that represent the meaning of that text) and store it. Then when someone asks The Brain "has Elena ever had knee problems?", we can search by meaning, not just by keyword.

We added these columns now so the database schema is ready. No migration needed when Phase 3 lands.

---

## Schemas — The API Contract

Schemas are the contract between the API and the outside world. They define: what can you send us? What will we send back?

For every model, there's typically three schemas:

1. **Create schema** — what you send to create a new record. Example: `ClientCreate` requires `name` (min 1 character), and optionally accepts `email`, `phone`, `goals`, etc.

2. **Update schema** — what you send to modify an existing record. Every field is optional (it's a PATCH, not a PUT — you only send what you want to change). Example: `ClientUpdate` has `name: str | None = None`.

3. **Response schema** — what you get back. Includes everything: `id`, `created_at`, all the fields. Uses `ConfigDict(from_attributes=True)` so SQLAlchemy models can be converted directly.

### The Entry Type Validation

The most complex schema is `SessionEntryCreate`. It has a model validator that runs after all fields are parsed:

- If `entry_type` is "exercise_card": `exercise_name` is required, `observation_text` must be absent.
- If `entry_type` is "observation_card": `observation_text` is required, `exercise_name` must be absent, `sets` must be absent.

This prevents garbage data. You can't have an exercise card with observation text, or an observation card with sets data.

But there's a subtlety on updates. When you PATCH an entry, you might not send `entry_type` at all — you're just updating the exercise name. The schema can't validate cross-type contamination without knowing the current type. So the router has a helper function `_reject_cross_type_fields()` that checks the entry's actual type from the database and rejects invalid field combinations. Defense in depth: the schema catches what it can, the router catches the rest.

### The Response Wrapper

Every API response follows the same shape:

```json
// Success (single item)
{
  "data": { "id": "...", "name": "...", ... },
  "meta": {}
}

// Success (list with pagination)
{
  "data": [ { ... }, { ... } ],
  "meta": { "cursor": "last-item-id", "limit": 20, "has_more": true }
}

// Error
{
  "error": { "code": "http_404", "message": "Client not found" }
}
```

This consistency matters. The mobile app can write one response parser that works for every endpoint. Errors always have a `code` and `message`. Lists always have pagination info.

---

## Pagination — How We Handle Large Lists

When a trainer has 200 clients or a client has 50 sessions, we can't return everything at once. We use cursor-based pagination.

### How it works

Say you have 100 clients, and you ask for page 1 with limit 20:

1. We query 21 clients (limit + 1), sorted by `created_at DESC` (newest first), with `id` as a tiebreaker.
2. We return the first 20, and because we got 21 back, we know there's more: `has_more: true`.
3. We set `cursor` to the last item's ID.

When you ask for page 2, you pass that cursor:

1. We look up the cursor's `created_at` value.
2. We query: "give me clients where `created_at` is older than the cursor's, or if the `created_at` is the same, where the `id` is after the cursor's."
3. Again, fetch limit + 1, return limit, set has_more.

### Why not offset pagination?

Offset pagination (`SKIP 20, LIMIT 20`) breaks in three ways:
- **Performance**: skipping 10,000 rows is slow. Cursor pagination is always fast because it uses a WHERE clause, not a skip.
- **Consistency**: if a new client is added while you're paginating, offset pagination can show you the same client twice or skip one entirely. Cursor pagination doesn't have this problem.
- **Scalability**: offset gets slower as data grows. Cursor doesn't.

### Why the ID tiebreaker?

Two clients might have the exact same `created_at` timestamp (created in the same millisecond). Without a tiebreaker, the cursor wouldn't know which one to start after. The UUID ID gives us a guaranteed unique ordering.

### The DRY Helper

Five services all needed the same pagination logic. Rather than copy-paste 20 lines into each one, we extracted a `paginate()` function in `services/pagination.py`. Each service now just builds its base query (with any filters it needs) and calls `paginate(db, query, Model, Model.sort_column, cursor=cursor, limit=limit)`. One function, five callers, zero duplication.

---

## Ownership Validation — The Security Layer

This is one of the most important parts of the system. Without proper auth (coming in Phase 4 with Supabase), we use a temporary approach: a hardcoded trainer ID. But the ownership validation layer is real and production-grade.

### The Problem

Trainer A should never see Trainer B's clients, sessions, or data. Even if Trainer A somehow guesses a valid UUID for Trainer B's client, the API should refuse.

### The Solution: dependencies.py

We have one file with 6 validation functions. Every router calls the appropriate one before doing anything:

- `get_trainer_id()` — returns the current trainer's UUID (mocked for now, will use Supabase JWT in Phase 4)
- `validate_client_ownership(client_id)` — fetches the client, checks `client.trainer_id == current_trainer`, raises 404 if not
- `validate_session_ownership(session_id)` — same pattern for sessions
- `validate_entry_ownership(entry_id)` — traces entry → session → client → trainer
- `validate_plan_ownership(plan_id)` — checks `plan.trainer_id == current_trainer`
- `validate_flag_ownership(flag_id)` — traces flag → client → trainer

### Why 404, not 403?

If we returned 403 ("you don't have permission"), an attacker could learn that the ID exists — they just can't access it. With 404, they can't tell the difference between "doesn't exist" and "exists but not yours." This is a standard security practice.

### Every Endpoint is Protected

This isn't aspirational — it's tested. For every entity type, we have tests that create data under Trainer B and then try to access it as Trainer A. Every one returns 404. GET, PATCH, DELETE, list — all tested for cross-trainer isolation.

---

## The Service Layer — Where Work Happens

Services are thin. They don't validate inputs (schemas do that). They don't check ownership (dependencies do that). They just talk to the database.

A typical service function looks like this:

```python
async def create_client(db: AsyncSession, trainer_id: uuid.UUID, **kwargs) -> Client:
    client = Client(trainer_id=trainer_id, **kwargs)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client
```

Four lines: create the object, add it to the session, save it, refresh it (to get server-generated fields like `id` and `created_at`), return it.

Update functions use `**kwargs` so the router can pass only the fields the user sent:

```python
async def update_client(db: AsyncSession, client: Client, **kwargs) -> Client:
    for key, value in kwargs.items():
        if value is not None:
            setattr(client, key, value)
    await db.commit()
    await db.refresh(client)
    return client
```

The `if value is not None` guard prevents accidentally clearing fields. If a PATCH sends `{"name": "New Name"}`, only `name` gets updated. The router uses `body.model_dump(exclude_unset=True)` to only pass fields the user explicitly included in their request. Fields they didn't mention aren't in kwargs at all.

There's one exception: `plan_service.update_plan` removes the None guard, because `planned_for_date` is a field you might legitimately want to set to null (un-schedule a plan). This works because `exclude_unset=True` already handles the "field not sent" case.

---

## Error Handling — Consistent, Never 500s

`main.py` has two custom error handlers:

1. **HTTP exceptions** (404, 403, etc.) → `{"error": {"code": "http_404", "message": "..."}}`
2. **Validation errors** (bad request body) → `{"error": {"code": "validation_error", "message": "field → error"}}`

The goal: no endpoint should ever return a 500 (server error) for bad user input. Every invalid input should get a proper 4xx error with a clear message. We tested this — pain level of 11 returns 422, negative duration returns 422, missing required fields return 422, non-existent IDs return 404.

---

## Testing — 306 Tests, 12 Files

### Test Infrastructure (conftest.py)

The test setup is worth understanding because it's the foundation all tests build on.

**Engine fixture** (runs once per test session): Creates a test database connection, enables the pgvector extension, creates all tables. At the end, drops everything.

**db_session fixture** (runs per test): Creates a fresh database session. After each test, truncates ALL tables. This means every test starts with an empty database — no test can affect another.

**client fixture**: Creates an HTTP test client that talks to the FastAPI app directly (no actual network calls). Overrides the `get_db` dependency so the app uses the test database session.

**trainer_for_api fixture**: Creates a trainer in the test database and sets the `TEMP_TRAINER_ID` so all API calls authenticate as this trainer.

**trainer_and_client / trainer_client_session**: Convenience fixtures that build up the chain — trainer + client, or trainer + client + session — so tests don't have to repeat that setup.

### What's Tested

**Model tests** (test_models.py, 22 tests): Can we create each model? Do FK constraints work? Do cascading deletes work? Do unique constraints work?

**Schema tests** (test_schemas.py, 65 tests): Does every schema accept valid input? Does it reject invalid input? Do cross-field validators work? Do boundary values (pain_level 1, 10, 0, 11) work?

**Endpoint tests** (5 files, ~200 tests): For every endpoint:
- Happy path — create/get/list/update/delete works
- Validation — missing fields, empty strings, out-of-range values return 422
- Not found — nonexistent UUIDs return 404
- Ownership — wrong trainer's data returns 404
- Pagination — cursor passing, has_more flag, no overlap between pages
- Cascades — deleting a parent removes/nullifies children
- Partial updates — sending one field doesn't affect others

**Edge cases** (test_edge_cases.py, 15 tests): Empty PATCH bodies (idempotent?), pagination with limit=0 or limit=-1 (no crash?), stale cursors (no crash?), cross-type contamination on update.

**Integration tests** (test_integration.py, 11 tests): Multi-entity scenarios. Delete a plan — does the session's plan_id become null? Archive a client — can you still access their sessions? Create a session with a plan that belongs to a different client — does it reject?

**Seed tests** (test_seed.py, 10 tests): Does the seed script run? Does it create the right counts? Are plans linked to the right clients? Is Elena's resolved injury actually resolved?

### Test Naming Convention

Every test name describes the behavior it's testing:

```
test_create_flag_session_wrong_client_422
test_update_partial_preserves_unchanged
test_delete_plan_sets_session_plan_id_null
test_list_entries_by_wrong_trainer_client_404
```

You can read the test name and know exactly what it's checking without looking at the code.

---

## The Seed Script — Realistic Demo Data

The seed script (`seed.py`) creates 5 clients with different profiles:

1. **Sarah Chen** (1 session) — Brand new client, just did an assessment. 4 basic exercises, low weights, careful form notes.

2. **Marcus Johnson** (3 sessions) — Experienced powerlifter. Squats going from 140→145→150kg. Has a knee discomfort flag from his ACL repair history.

3. **Aisha Patel** (5 sessions) — Post-pregnancy recovery. Goblet squats, dead bugs, band work. Started with a plan mid-way through. Observations track energy and recovery.

4. **Jake Morrison** (10 sessions) — Eager beginner. Making fast gains (bench 40→62.5kg in 10 sessions). Has 2 session plans (upper day, lower day). Form notes show improvement over time.

5. **Elena Vasquez** (15 sessions) — 68-year-old, long-term client. Slow, steady progression on leg press (30→55kg). Has a resolved shoulder injury and an active hip flag. 3 plans over her progression. Observations track confidence and balance.

This data isn't random — it's designed to demonstrate every feature of the system. Different session counts, different progression patterns, injuries that resolve, plans that link to sessions, observations mixed with exercises. When we build the AI features, this data gives us something real to work with.

---

## Key Architecture Decisions — The "Why" Behind the Choices

### Why async everything?

Every database call uses `await`. Every handler is `async`. This means when one request is waiting for the database, the server can handle other requests. For a product that will process voice audio (slow) and call external APIs (Deepgram, Claude — slow), async is essential. If we used synchronous code, the server would freeze while waiting for Deepgram to transcribe audio.

### Why UUIDs instead of auto-incrementing integers?

Three reasons:
1. **Security**: Sequential IDs are guessable. If client 42 exists, client 43 probably does too. UUIDs are random — you can't guess them.
2. **Distributed systems**: If we ever need multiple database servers, UUIDs don't collide. Auto-incrementing IDs do.
3. **API design**: UUIDs in URLs (`/clients/550e8400-e29b-...`) are standard for modern APIs.

### Why one table for two entry types?

Exercise cards and observation cards could live in separate tables. We chose one table with an `entry_type` discriminator because:
- The session timeline is a sequence of both types interleaved. One table means one query to get the full timeline.
- Both types share common fields (`sequence_order`, `performed_at`, `created_at`).
- The trade-off (nullable fields) is worth it for the query simplicity.

### Why plans are independent from sessions?

A plan is "what the trainer intends." A session is "what actually happened." These are fundamentally different things. The trainer might:
- Create a plan but never run that session (client cancelled)
- Run a session that doesn't match any plan (spontaneous workout)
- Run a session that partially follows a plan (client was tired, changed exercises)

By keeping them independent and linking via an optional `plan_id`, we can support all of these scenarios. And in Phase 3, we can compare plan vs. actual to give insights like "Elena completed 80% of the planned exercises."

### Why the ownership chain instead of just checking trainer_id on everything?

Not every model has a `trainer_id`. SessionEntry doesn't — it belongs to a session, which belongs to a client, which belongs to a trainer. We could add `trainer_id` to every table, but that's data duplication and creates the risk of it getting out of sync.

Instead, we trace the chain. To check if you own an entry, we check if you own the client that the entry belongs to. The chain is always consistent because it follows the foreign key relationships that the database enforces.

---

## What's Coming Next

Phase 1a gave us the data foundation. Here's what plugs into it:

**Phase 2 (Mobile)**: React Native app that talks to these endpoints. Client list screen, session recording screen, entry timeline view.

**Phase 3 (Voice + Intelligence)**: This is where it gets interesting.
- Deepgram transcribes voice → Claude parses transcript into structured entries
- Pre-session briefings generated from client history (using the data we're storing now)
- The Brain — a conversational agent that can answer "how has Elena's squat progressed?" by querying the actual session entries
- Embeddings stored in those pgvector columns for semantic search

**Phase 4 (Auth + Multi-tenant)**: Replace `TEMP_TRAINER_ID` with real Supabase authentication. Each trainer logs in and only sees their data. The ownership validation layer is already built — we just need to plug in the real identity.

The reason Phase 1a matters: every AI feature in Phase 3 reads from and writes to the models, schemas, and endpoints we built. If the foundation is shaky — missing validations, inconsistent data shapes, untested cascades — every AI feature built on top would be fragile. The foundation is solid. 306 tests prove it.

---

## Quick Reference

### Files and What They Do

| File | Purpose |
|------|---------|
| `main.py` | App entry point, error handlers, middleware, router registration |
| `config.py` | Environment variables via pydantic-settings |
| `database.py` | Async SQLAlchemy engine + session factory |
| `models.py` | 10 SQLAlchemy models, 5 enums |
| `schemas.py` | 34 Pydantic schemas (create/update/response for each entity) |
| `api/dependencies.py` | Ownership validation (6 functions) |
| `api/clients.py` | 6 endpoints for client CRUD + archive |
| `api/sessions.py` | 4 endpoints for session CRUD |
| `api/entries.py` | 6 endpoints for entry CRUD (2 list paths) |
| `api/plans.py` | 5 endpoints for plan CRUD |
| `api/injury_flags.py` | 5 endpoints for injury flag CRUD |
| `services/pagination.py` | Generic cursor-based pagination |
| `services/client_service.py` | Client database operations |
| `services/session_service.py` | Session database operations |
| `services/entry_service.py` | Entry database operations + sequence ordering |
| `services/plan_service.py` | Plan database operations |
| `services/injury_flag_service.py` | Injury flag database operations |
| `seed.py` | Demo data: 5 clients, 34 sessions, 115 entries |
| `tests/conftest.py` | Test fixtures (engine, db, client, trainer) |

### Endpoints

| Method | Path | What It Does |
|--------|------|-------------|
| GET | `/api/v1/clients` | List trainer's clients (paginated) |
| POST | `/api/v1/clients` | Create a client |
| GET | `/api/v1/clients/{id}` | Get one client |
| PATCH | `/api/v1/clients/{id}` | Update client fields |
| PATCH | `/api/v1/clients/{id}/archive` | Soft-delete a client |
| GET | `/api/v1/clients/{id}/sessions` | List client's sessions (paginated) |
| POST | `/api/v1/sessions` | Create a session |
| GET | `/api/v1/sessions/{id}` | Get one session |
| PATCH | `/api/v1/sessions/{id}` | Update session fields |
| DELETE | `/api/v1/sessions/{id}` | Delete session + cascade |
| POST | `/api/v1/sessions/{id}/entries` | Create an entry in a session |
| GET | `/api/v1/sessions/{id}/entries` | List entries for a session |
| GET | `/api/v1/clients/{id}/entries` | List all entries for a client (paginated) |
| GET | `/api/v1/entries/{id}` | Get one entry |
| PATCH | `/api/v1/entries/{id}` | Update an entry |
| DELETE | `/api/v1/entries/{id}` | Delete an entry |
| POST | `/api/v1/plans` | Create a session plan |
| GET | `/api/v1/clients/{id}/plans` | List plans for a client (paginated) |
| GET | `/api/v1/plans/{id}` | Get one plan |
| PATCH | `/api/v1/plans/{id}` | Update a plan |
| DELETE | `/api/v1/plans/{id}` | Delete a plan |
| POST | `/api/v1/injury-flags` | Create an injury flag |
| GET | `/api/v1/clients/{id}/injury-flags` | List flags for a client (paginated) |
| GET | `/api/v1/injury-flags/{id}` | Get one flag |
| PATCH | `/api/v1/injury-flags/{id}` | Update a flag |
| DELETE | `/api/v1/injury-flags/{id}` | Delete a flag |

### Numbers

- 10 models, 5 enums
- 34 Pydantic schemas
- 26 API endpoints across 5 routers
- 306 tests across 12 test files
- 5 demo clients with 34 sessions and 115 entries
- 19 canonical exercises seeded
