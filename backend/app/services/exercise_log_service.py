import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExerciseLog


async def list_by_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[ExerciseLog], bool]:
    """Return (exercise_logs, has_more) for a session, ordered by created_at."""
    query = (
        select(ExerciseLog)
        .where(ExerciseLog.session_id == session_id)
        .order_by(ExerciseLog.created_at, ExerciseLog.id)
    )

    if cursor:
        cursor_log = await db.get(ExerciseLog, cursor)
        if cursor_log:
            query = query.where(
                (ExerciseLog.created_at > cursor_log.created_at)
                | ((ExerciseLog.created_at == cursor_log.created_at) & (ExerciseLog.id > cursor_log.id))
            )

    result = await db.execute(query.limit(limit + 1))
    logs = list(result.scalars().all())

    has_more = len(logs) > limit
    if has_more:
        logs = logs[:limit]

    return logs, has_more


async def list_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    exercise_name: str | None = None,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[ExerciseLog], bool]:
    """Return (exercise_logs, has_more) for a client, newest first."""
    query = (
        select(ExerciseLog)
        .where(ExerciseLog.client_id == client_id)
        .order_by(ExerciseLog.created_at.desc(), ExerciseLog.id)
    )

    if exercise_name:
        query = query.where(ExerciseLog.exercise_name.ilike(exercise_name))

    if cursor:
        cursor_log = await db.get(ExerciseLog, cursor)
        if cursor_log:
            query = query.where(
                (ExerciseLog.created_at < cursor_log.created_at)
                | ((ExerciseLog.created_at == cursor_log.created_at) & (ExerciseLog.id > cursor_log.id))
            )

    result = await db.execute(query.limit(limit + 1))
    logs = list(result.scalars().all())

    has_more = len(logs) > limit
    if has_more:
        logs = logs[:limit]

    return logs, has_more


async def get_exercise_log(db: AsyncSession, exercise_log_id: uuid.UUID) -> ExerciseLog | None:
    return await db.get(ExerciseLog, exercise_log_id)


async def create_exercise_log(db: AsyncSession, **kwargs) -> ExerciseLog:
    log = ExerciseLog(**kwargs)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
