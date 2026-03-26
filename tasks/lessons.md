# SuperTrainer — Lessons Learned

Patterns and rules discovered during development. Each entry uses root-cause-first format. Grouped by theme, not by date. Updated after every correction — code fixed first, doc updated second, lesson recorded last.

---

## Audit Discipline

### The Audit Must Be Automatic and Adversarial
**Mistake**: Declared "done" without doing the staff engineer review — happened 5 times across Days 1, 4, 5 (Phase 1a), Day 2 (Phase 1b), Day 11 (Phase 2a). Each time, real issues were sitting in plain sight (missing cascade tests, untested ownership paths, unused imports, missing edge cases).
**Root Cause**: Treating the audit as a checkbox instead of adversarial review. Running the audit agent (step 1) but skipping the personal staff engineer re-read (step 2).
**Correct Approach**: Two-step audit, every time, automatically: (1) audit agent, (2) personal re-read of every file looking for things that are WRONG. If the audit finds nothing, you didn't look hard enough. Finish code → re-read everything → cross-reference spec → find gaps → fix → THEN report.
**Fixed In**: Global CLAUDE.md workflow protocol, MEMORY.md pre-done checklist.

### Report Audit Findings Explicitly
**Mistake**: Said "I did the audit" without listing what was checked or found.
**Root Cause**: Audit treated as a declaration rather than a deliverable.
**Correct Approach**: List what was checked, what was found, what was fixed, and what was already clean. If the report doesn't name specific findings, it didn't happen.
**Fixed In**: Phase 1a Day 4 audit process.

### Run a Second Audit After Batch Fixes
**Mistake**: Fixed 9 audit issues, stopped. Second pass found 1 more (plan_id ownership).
**Root Cause**: Fixes themselves can introduce or reveal new problems.
**Correct Approach**: Always run a second pass after a batch of fixes.
**Fixed In**: Phase 1a Day 5 golden audit.

---

## Definition of Done

### "Done" Means Committed and Pushed
**Mistake**: Declared "done" repeatedly with uncommitted changes, un-updated STATUS.md, unwritten lessons, or un-renamed scratch devlogs.
**Root Cause**: Treating "done" as "code is written" instead of "everything is shipped."
**Correct Approach**: Checklist before saying "done": (1) tests pass, (2) STATUS.md updated, (3) tasks/todo.md updated, (4) tasks/lessons.md updated if new lessons, (5) devlog written and renamed from scratch, (6) all changes committed, (7) pushed to remote, (8) `git status` clean.
**Fixed In**: MEMORY.md pre-done checklist, repeated across Phases 1a, 1b, 2a.

---

## Testing Strategy

### Treat Testing as Its Own Task
**Mistake**: Folded testing into the build plan. Implementation plan produced 15 integration tests — solid but standard.
**Root Cause**: AI defaults to "build + test as I go" which produces adequate but not thorough coverage.
**Correct Approach**: Always create a dedicated testing plan as a separate task after implementation is done. Explore the codebase specifically for coverage gaps. On Phase 1b Day 5, the dedicated pass found 7 categories of missing tests and produced 27 targeted additions.
**Fixed In**: Phase 1b Day 5 testing workflow.

### Vacuous Assertion Detection
**Mistake**: Test used `weight=85, weight_unit="kg"` for both input and expected output. Test passed regardless of whether the guard worked.
**Root Cause**: When raw == normalized, the assertion is vacuous — it can't detect a broken guard.
**Correct Approach**: Always use values where raw != normalized. Use lbs values (raw=185, normalized=83.9) so a broken guard produces a visibly wrong result.
**Fixed In**: Phase 1b Day 5 validation tests.

### Test the Spec Table, Not Just the Models
**Mistake**: Wrote 18 tests, said "all done," missed 4 cascade behaviors with zero coverage.
**Root Cause**: Assumed the plan's test count was a ceiling rather than a floor.
**Correct Approach**: When there's a cascade/behavior spec table, every single row must have a dedicated test. The plan is a starting point.
**Fixed In**: Phase 1a Day 1 cascade tests.

### Test Validation at Integration Level, Not Just Schema Level
**Mistake**: Schema test proved `sequence_order=0` fails at Pydantic layer, but no integration test proved the API returns 422 (not 500).
**Root Cause**: Schema validation and API validation are two separate trust boundaries.
**Correct Approach**: Test both. A schema test proves the schema rejects it; an integration test proves the API handles it correctly.
**Fixed In**: Phase 1a Day 4 entry validation tests.

---

## Ownership & Security Testing

### Ownership Test Symmetry Across HTTP Verbs
**Mistake**: Tested GET and POST for cross-trainer ownership but missed PATCH and DELETE. Later: plans had all 5 verbs, injury flags only had 3.
**Root Cause**: Not systematically enumerating endpoints when writing ownership tests.
**Correct Approach**: List every endpoint in the router. Verify each one has a wrong-trainer test. No exceptions. All HTTP verbs.
**Fixed In**: Phase 1a Days 4-5, dependencies.py extraction.

### FK Ownership vs FK Existence
**Mistake**: Sessions.py validated that `plan_id` exists but not that it belongs to the current trainer.
**Root Cause**: Existence checks prevent 500s. Ownership checks prevent cross-tenant data leaks. Two separate concerns.
**Correct Approach**: Every FK reference in a create/update endpoint must check BOTH existence AND ownership.
**Fixed In**: Phase 1a Day 5 golden audit, plan_id ownership validation.

### Backport Security Patterns to Existing Endpoints
**Mistake**: Clients and sessions routers shipped without ownership validation — a trainer could access any client/session by guessing the UUID. Later routers got it right because the pattern was established.
**Root Cause**: Earlier routers written before the pattern existed, never backported.
**Correct Approach**: When establishing a new security pattern, backport it to ALL existing endpoints immediately.
**Fixed In**: Phase 1a Day 5 golden audit, dependencies.py.

---

## Frontend-Backend Data Contract

### Read Backend Before Building Frontend
**Mistake**: Built session entry display using TypeScript `SetData` interface — but actual backend data uses different keys. Seed data uses `"set"` and `"weight_kg"`. Voice pipeline uses `"weight"` and has NO set number key. Two formats, neither matching the TypeScript type.
**Root Cause**: TypeScript types are aspirational. The JSONB `sets` field is `list[dict]` with no enforced schema. The backend is reality; the type is a wish.
**Correct Approach**: Before displaying any backend data, read: (1) Pydantic response schema, (2) the service that creates the data (seed.py, voice.py), (3) the actual DB format. Build from what the backend ACTUALLY returns.
**Fixed In**: Phase 2a Day 4, `getSetWeight` reads `weight` before `weight_kg`.

### Cross-System Entity Naming Must Match
**Mistake**: `seed.py` stores `goblet_squat`, `exercise_db.json` stores `Goblet Squat`. Workout classifier does exact-match dict lookup — silently fails, returns "Session" for everything.
**Root Cause**: Two systems reference the same entity with different formats. No validation at the boundary.
**Correct Approach**: Whenever two systems reference the same entity by name, verify the format matches. Especially dangerous with JSONB fields that have no schema enforcement. One-line fix: `.replace("_", " ")` before lookup.
**Fixed In**: Phase 2a Day 11, `workout_classifier.py`.

---

## Debugging

### Backtrace Before Fixing
**Mistake**: Something broke during design system migration. Spent an hour going in circles trying different fixes without identifying the root cause. Pranav intervened, forced a backtrace, found it in a minute.
**Root Cause**: Panic response — try to fix immediately instead of understanding first.
**Correct Approach**: When a fix attempt fails, DO NOT try another fix. Instead: (1) state what you expected, (2) state what actually happened, (3) trace backward from symptom to divergence point, (4) only then propose a fix.
**Fixed In**: Phase 2a Day 1, design system debugging session.

---

## UI/UX Design

### Iterate with Screenshots, Start Minimal
**Mistake**: Compact exercise format went through ~8 visual iterations — blue backgrounds, pill chips, split fonts, table layouts — all looked worse than simple text lines. `caption` variant adds ALL CAPS (not obvious from name).
**Root Cause**: Guessing at visual design in code without seeing it on device. What looks reasonable in code often looks terrible on screen.
**Correct Approach**: Test every UI variant on actual phone. Ask for screenshots early and often. Start minimal, add visual weight only when needed. Premium = intentional restraint, not complexity.
**Fixed In**: Phase 2a compact exercise format iterations.

---

## Communication & Context

### Proactively Flag Context Window Issues
**Mistake**: Failed to warn about heavy context twice (Day 5/6 and Day 9/10 boundaries). Pranav had to ask "new terminal?" both times.
**Root Cause**: Not monitoring context load proactively.
**Correct Approach**: Before the user finishes a day or asks what's next, check if context is heavy. Say "heads up, context is full" BEFORE they have to ask.
**Fixed In**: MEMORY.md non-negotiable rule.

### Save Important Reflections Immediately
**Mistake**: Pranav gave a deep reflection he called "golden, very important." It got lost when context compacted.
**Root Cause**: Context compaction is unpredictable. Waiting for the devlog is too late.
**Correct Approach**: When Pranav shares something he calls important, write it to a scratch file (`devlog/scratch-YYYY-MM-DD.md`) immediately. Don't wait.
**Fixed In**: Phase 1b Day 2, MEMORY.md rule.

---

## Git Workflow

### Docs on Master, Code on Feature Branch
**Mistake**: Put STATUS.md, devlogs, and documentation on the feature branch instead of master.
**Root Cause**: Default behavior — commit everything to the current branch.
**Correct Approach**: Docs go on master. Code goes on feature branch. Do it right the first time — cherry-picking after the fact causes merge conflicts.
**Fixed In**: Phase 1b workflow, MEMORY.md rule.

### No AI Attribution in Commits
**Mistake**: Two early commits shipped with `Co-Authored-By: Claude` lines.
**Root Cause**: Default git commit behavior.
**Correct Approach**: No AI attribution, ever. No Co-Authored-By, no Claude mentions in commits, PRs, or comments.
**Fixed In**: Phase 1a Day 3, git filter-branch to strip from history.

---

## DRY Violations

### Extract Shared Code on Day One of the Pattern
**Mistake**: Identical `_validate_client_ownership` copy-pasted into 3 routers over Days 4-5. Each day "just one copy." By Day 5: 27 lines of identical code in 3 files.
**Root Cause**: DRY violations compound across days. Each copy feels harmless in isolation.
**Correct Approach**: If the same function appears in 2+ files, extract immediately. Don't wait for a third copy.
**Fixed In**: Phase 1a Day 5 golden audit, `dependencies.py`.

---

## Technical Gotchas

### pytest-asyncio Loop Scope
When using session-scoped async fixtures with asyncpg, ALL test functions must use `loop_scope="session"`. Add `pytestmark = pytest.mark.asyncio(loop_scope="session")` at top of each test file. Otherwise: `Future attached to a different loop`.

### IntegrityError + Savepoints
After an IntegrityError, the transaction is invalidated. Use `begin_nested()` (savepoint) before the operation that will fail, then `rollback()` after.

### httpx 0.28+ Requires ASGITransport
Can't use `AsyncClient(app=app)` anymore. Must use `httpx.ASGITransport(app=app)` and pass `transport=transport`. Old pattern silently fails.

### DB Session Sharing in Test Fixtures
HTTP `client` fixture must override `get_db` to yield the same `db_session` the test uses. Otherwise test data isn't visible to HTTP handlers.

### Native Postgres Port Conflict
Pranav has native Postgres on port 5432. Docker dev DB uses port 5434, test DB uses 5433.

### Schema Update Validators Need Entry Type Context
`SessionEntryUpdate` cross-field validation only runs when `entry_type` is in the update payload. Without it, we can't know the current type from the schema alone. Deliberate design choice, not a gap.
