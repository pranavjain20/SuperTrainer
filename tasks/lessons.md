# SuperTrainer — Lessons Learned

Mistakes, patterns, and rules discovered during development.
Updated after every correction.

## Day 1

- **pytest-asyncio loop scope**: When using session-scoped async fixtures with asyncpg, ALL test functions must also use `loop_scope="session"`. Otherwise the test runs on a function-scoped loop while the DB connection lives on the session loop → `Future attached to a different loop`. Fix: add `pytestmark = pytest.mark.asyncio(loop_scope="session")` at the top of each test file.

- **IntegrityError + savepoints**: After an IntegrityError, the underlying transaction is invalidated. Use `begin_nested()` (savepoint) before the operation that will fail, then `rollback()` after. Otherwise subsequent operations on the same session fail.

- **Native Postgres port conflict**: Pranav has a native Postgres on port 5432. Docker dev DB uses port 5434 to avoid conflict. Remember this for all connection strings.

## Day 1 (v3 rebuild)

- **DO THE AUDIT AUTOMATICALLY**: After finishing implementation, STOP and switch to reviewer mode BEFORE saying "done". Re-read every file. Check every cascade path in the spec against actual tests. Check every FK constraint. On Day 1 v3, I wrote 18 tests, said "all done", and missed 4 cascade behaviors with zero test coverage. The CLAUDE.md says to do this automatically — not when asked. This is non-negotiable. The pattern: finish code → re-read everything → cross-reference spec → find gaps → fix gaps → THEN report.

- **Test the spec table, not just the models**: When there's a cascade/behavior spec table, every single row must have a dedicated test proving it works. Don't assume "18 tests" is enough just because the plan said 18. The plan is a starting point, not a ceiling.

## Day 3 (v3 rebuild)

- **Never include Co-Authored-By in commits.** Two early commits shipped with `Co-Authored-By: Claude` lines. Had to use `git filter-branch --msg-filter` to strip them and force-push both branches. This is in CLAUDE.md and MEMORY.md — no AI attribution, ever. No exceptions.

- **httpx 0.28+ requires ASGITransport**: Can't use `AsyncClient(app=app)` anymore. Must use `httpx.ASGITransport(app=app)` and pass `transport=transport` to `AsyncClient`. The old pattern silently fails.

- **DB session sharing in test fixtures**: The HTTP `client` fixture must override `get_db` to yield the same `db_session` the test is using. Otherwise test data created via `db_session.add()` isn't visible to HTTP handlers — they get a different session and see an empty database.

## Day 4 (v3 rebuild)

- **Audit must cover every HTTP verb per ownership path**: On Day 4, first audit pass only tested GET and POST for cross-trainer ownership but missed PATCH and DELETE. All four verbs go through `_validate_entry_ownership`, but without explicit tests, a regression could silently let trainers modify each other's entries. Rule: if an endpoint validates ownership, there must be an integration test proving wrong-trainer returns 404 for that specific HTTP method.

- **Test validation edge cases at the integration level, not just schema level**: Schema tests proved `sequence_order=0` fails at the Pydantic layer, but there was no integration test proving the API returns 422 (not 500) for this input. Schema validation and API validation are two separate trust boundaries — test both.

- **Report audit findings explicitly**: Don't just say "I did the audit." List what was checked, what was found, what was fixed, and what was already clean. If the report doesn't name specific findings, it didn't happen.

## Day 5 (v3 rebuild)

- **The audit is not a checkbox — it's adversarial review.** Day 5: declared "audit complete" with 3 real issues sitting in plain sight (missing return type annotations, 2 untested ownership paths). Had to be called out again, same mistake as Day 1 and Day 4. The audit means: read each file line by line looking for things that are WRONG. Compare every function signature against the reference file (entries.py). Check that every HTTP verb x every ownership path has a test. If the audit doesn't find at least one issue, you probably didn't look hard enough. Finding nothing is suspicious, not a success.

- **Symmetry check for ownership tests**: When testing ownership (wrong-trainer → 404), ensure ALL endpoints are covered symmetrically. On Day 5, plans had tests for create/get/patch/delete/list with wrong trainer. Injury flags only had create/get/delete — missing patch and list. The check: list every endpoint in the router, verify each one has a wrong-trainer test. No exceptions.

## Day 5 Golden Audit

- **DRY violations compound across days.** Identical `_validate_client_ownership` was copy-pasted into 3 routers over Days 4-5. Each day it was "just one copy." By Day 5, it's 27 lines of identical code in 3 files. Fix: extract shared validation into `dependencies.py` on day one of the pattern. The rule is: if the same function appears in 2+ files, extract immediately.

- **Ownership validation must be checked when adding new endpoints.** Clients and sessions routers shipped without ownership validation on get/update/delete — a trainer could access any client/session by guessing the UUID. Entries, plans, and injury flags (written later) got it right because the pattern was established. The gap: the earlier routers were written before the pattern existed and never got updated. Rule: when establishing a new security pattern, backport it to ALL existing endpoints immediately.

- **FK ownership is a separate concern from FK existence.** Sessions.py validated that `plan_id` exists but not that it belongs to the current trainer. This is a subtle distinction: existence checks prevent 500s, ownership checks prevent cross-tenant data leaks. Every FK reference in a create/update endpoint must check BOTH existence AND ownership.

- **Schema update validators need entry_type context.** SessionEntryUpdate initially had no cross-field validator. The fix adds validation only when `entry_type` is explicitly included in the update payload. Without entry_type, we can't know the current type from the schema alone, so validation is skipped. This is a deliberate design choice, not a gap — document it.

- **Second audit passes catch real issues.** The first audit found 9 issues. After fixing all 9, the second audit found 1 more (plan_id ownership). Always run a second pass after a batch of fixes — the fixes themselves can introduce or reveal new problems.

## Definition of Done

- **"Done" means committed.** On Day 5, declared golden audit complete and ready for Day 6 while 18 files of changes sat uncommitted. Pranav had to ask "have you committed?" — that should never happen. The rule: if it's not committed, it's not done. Before saying "done" or "clean" or "ready to move on," the checklist is: (1) tests pass, (2) changes committed, (3) nothing left hanging. This is what separates a co-architect from someone who needs micromanaging. Big statements ("everything is clean") require big verification.

## Day 2 (Phase 1b)

- **The audit is STILL not automatic.** Day 2 Phase 1b: wrote parser.py + test_parser.py, ran the audit agent, fixed the audit findings, and was about to say "done" — without doing the staff engineer review myself. Pranav had to ask "have we done the staff engineer check?" That's the FOURTH time (Days 1, 4, 5, and now Day 2 Phase 1b). The audit agent is step 1. The personal staff engineer re-read is step 2. Both must happen, automatically, before ANY mention of "done" or "wrapping up." Found: 6 unused imports in test file, missing "all sets malformed" edge case test. Both real issues that would have shipped unnoticed.

- **Save important reflections immediately — don't trust the context window.** Pranav gave a deep, important reflection about the tension between AI-assisted learning speed and depth of understanding. He explicitly said "this is golden, very important stuff for me to remember." It got lost when the context compacted. The rule: when Pranav shares something he calls important, write it to a scratch file (`devlog/scratch-YYYY-MM-DD.md`) immediately. Don't wait for the devlog. Context compaction is unpredictable. If it matters, save it now.

## Day 5 (Phase 1b) — Testing Workflow

- **Treat testing as its own task, not a subtask of implementation.** AI defaults to "build the thing and test as I go." A human nudging "now step back and think about testing separately" produces meaningfully better coverage. On Day 5, the implementation plan produced 15 integration tests — solid, but standard. When Pranav pushed for a dedicated testing pass, the result was a separate plan that explored the codebase specifically for coverage gaps, found 7 categories of missing tests, and produced 27 targeted additions. Two plans instead of one. Without the nudge, a vacuous assertion that hid a real guard failure would have shipped. The pattern: always create a dedicated testing plan as a separate task after implementation is done. Don't fold testing into the build plan.

- **Vacuous assertion detection.** When testing guards/normalization, always use values where raw ≠ normalized. If `weight=85, weight_unit="kg"` is used for both input and expected output, the test passes regardless of whether the guard works. Use lbs values (raw=185, normalized=83.9) so a broken guard produces a visibly wrong result.

## Git Workflow

- **Docs go on master, code goes on feature branch.** STATUS.md, README.md, devlogs, and other documentation updates must be committed and pushed to master — not the feature branch. Code changes go on the feature branch. This was established in the workflow but I kept putting everything on the feature branch. Cherry-picking after the fact causes merge conflicts. Do it right the first time.

## Phase 2a — Frontend Must Match Backend Data

- **Always read backend schemas/services BEFORE building frontend display code.** On Day 4, built the session entry display using the TypeScript `SetData` interface (which had `set_number`, `weight_kg`) — but the actual backend data uses different keys. Seed data uses `"set"` (not `"set_number"`) and `"weight_kg"`. Voice pipeline uses `"weight"` (not `"weight_kg"`) and has NO set number key at all. Two different formats, neither matching the TypeScript type. The rule: before displaying any backend data, read (1) the Pydantic response schema, (2) the service that creates the data (seed.py, voice.py), and (3) the actual DB format. Build the frontend from what the backend ACTUALLY returns, not from what the TypeScript type says it should be. The TypeScript types are aspirational — the JSONB `sets` field is `list[dict]` with no enforced schema.

## Context Window Management

- **Proactively flag context window issues.** Failed TWICE now — Day 5/6 boundary and Day 9/10 boundary. Both times Pranav had to ask "new terminal?" instead of me telling him first. This is in MEMORY.md as a non-negotiable. The rule: BEFORE the user finishes a day or asks what's next, check if context is heavy. If it is, say "heads up, context is full — start a fresh terminal for Day X" BEFORE they have to ask. No more misses on this.
