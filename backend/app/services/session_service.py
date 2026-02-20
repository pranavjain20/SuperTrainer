import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session


async def list_sessions_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[Session], bool]:
    """Return (sessions, has_more) for a client, newest first."""
    query = (
        select(Session)
        .where(Session.client_id == client_id)
        .order_by(Session.started_at.desc(), Session.id)
    )

    if cursor:
        cursor_session = await db.get(Session, cursor)
        if cursor_session:
            query = query.where(
                (Session.started_at < cursor_session.started_at)
                | ((Session.started_at == cursor_session.started_at) & (Session.id > cursor_session.id))
            )

    result = await db.execute(query.limit(limit + 1))
    sessions = list(result.scalars().all())

    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:limit]

    return sessions, has_more


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    return await db.get(Session, session_id)


async def create_session(db: AsyncSession, trainer_id: uuid.UUID, **kwargs) -> Session:
    session = Session(trainer_id=trainer_id, **kwargs)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def update_session(db: AsyncSession, session: Session, **kwargs) -> Session:
    # NOTE: skips None values, so you can't clear optional fields via PATCH yet.
    for key, value in kwargs.items():
        if value is not None:
            setattr(session, key, value)
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session: Session) -> None:
    await db.delete(session)
    await db.commit()
