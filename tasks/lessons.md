# SuperTrainer — Lessons Learned

Mistakes, patterns, and rules discovered during development.
Updated after every correction.

## Day 1

- **pytest-asyncio loop scope**: When using session-scoped async fixtures with asyncpg, ALL test functions must also use `loop_scope="session"`. Otherwise the test runs on a function-scoped loop while the DB connection lives on the session loop → `Future attached to a different loop`. Fix: add `pytestmark = pytest.mark.asyncio(loop_scope="session")` at the top of each test file.

- **IntegrityError + savepoints**: After an IntegrityError, the underlying transaction is invalidated. Use `begin_nested()` (savepoint) before the operation that will fail, then `rollback()` after. Otherwise subsequent operations on the same session fail.

- **Native Postgres port conflict**: Pranav has a native Postgres on port 5432. Docker dev DB uses port 5434 to avoid conflict. Remember this for all connection strings.
