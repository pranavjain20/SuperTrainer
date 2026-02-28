import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionEntry
from app.services.pagination import paginate


async def get_entry(db: AsyncSession, entry_id: uuid.UUID) -> SessionEntry | None:
    return await db.get(SessionEntry, entry_id)


async def get_next_sequence_order(db: AsyncSession, session_id: uuid.UUID) -> int:
    """Return max(sequence_order) + 1 for a session, or 1 if no entries exist."""
    result = await db.execute(
        select(func.max(SessionEntry.sequence_order))
        .where(SessionEntry.session_id == session_id)
    )
    current_max = result.scalar_one_or_none()
    return (current_max or 0) + 1


async def create_entry(
    db: AsyncSession, session_id: uuid.UUID, client_id: uuid.UUID, **kwargs
) -> SessionEntry:
    entry = SessionEntry(session_id=session_id, client_id=client_id, **kwargs)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_entries_by_session(
    db: AsyncSession, session_id: uuid.UUID
) -> list[SessionEntry]:
    """Return all entries for a session, ordered by sequence_order asc."""
    result = await db.execute(
        select(SessionEntry)
        .where(SessionEntry.session_id == session_id)
        .order_by(SessionEntry.sequence_order.asc())
    )
    return list(result.scalars().all())


async def list_entries_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[SessionEntry], bool]:
    """Return (entries, has_more) for a client, newest first."""
    query = select(SessionEntry).where(SessionEntry.client_id == client_id)
    return await paginate(db, query, SessionEntry, SessionEntry.created_at, cursor=cursor, limit=limit)


async def update_entry(db: AsyncSession, entry: SessionEntry, **kwargs) -> SessionEntry:
    for key, value in kwargs.items():
        if value is not None:
            setattr(entry, key, value)

    # Recalculate total_volume_kg whenever sets change
    if "sets" in kwargs and kwargs["sets"] is not None:
        total = 0.0
        has_weight = False
        for s in kwargs["sets"]:
            w = s.get("weight") or s.get("weight_kg")
            r = s.get("reps") or 0
            if w is not None:
                total += r * w
                has_weight = True
        entry.total_volume_kg = round(total, 1) if has_weight else None

    await db.commit()
    await db.refresh(entry)
    return entry


async def delete_entry(db: AsyncSession, entry: SessionEntry) -> None:
    await db.delete(entry)
    await db.commit()
