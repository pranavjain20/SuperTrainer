import uuid
from datetime import date

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import DATE
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session
from app.services.pagination import paginate


async def list_sessions_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[Session], bool]:
    """Return (sessions, has_more) for a client, newest first."""
    query = select(Session).where(Session.client_id == client_id)
    return await paginate(db, query, Session, Session.started_at, cursor=cursor, limit=limit)


async def list_sessions_by_trainer(
    db: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    scheduled_for_date: date | None = None,
    tz: str = "UTC",
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[Session], bool]:
    """Return (sessions, has_more) for a trainer, newest first.

    When scheduled_for_date is provided, returns sessions where scheduled_for
    or started_at falls on that date in the given timezone.
    """
    query = select(Session).where(Session.trainer_id == trainer_id)
    if scheduled_for_date is not None:
        # Convert stored UTC timestamps to trainer's local timezone before
        # extracting the date, so "today" matches the trainer's actual day.
        local_started = cast(func.timezone(tz, Session.started_at), DATE)
        local_scheduled = cast(func.timezone(tz, Session.scheduled_for), DATE)
        query = query.where(
            or_(
                local_scheduled == scheduled_for_date,
                local_started == scheduled_for_date,
            )
        )
    return await paginate(db, query, Session, Session.started_at, cursor=cursor, limit=limit)


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
