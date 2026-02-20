import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InjuryFlag


async def list_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[InjuryFlag], bool]:
    """Return (injury_flags, has_more) for a client, newest first."""
    query = (
        select(InjuryFlag)
        .where(InjuryFlag.client_id == client_id)
        .order_by(InjuryFlag.flagged_at.desc(), InjuryFlag.id)
    )

    if cursor:
        cursor_flag = await db.get(InjuryFlag, cursor)
        if cursor_flag:
            query = query.where(
                (InjuryFlag.flagged_at < cursor_flag.flagged_at)
                | ((InjuryFlag.flagged_at == cursor_flag.flagged_at) & (InjuryFlag.id > cursor_flag.id))
            )

    result = await db.execute(query.limit(limit + 1))
    flags = list(result.scalars().all())

    has_more = len(flags) > limit
    if has_more:
        flags = flags[:limit]

    return flags, has_more


async def create_injury_flag(db: AsyncSession, **kwargs) -> InjuryFlag:
    flag = InjuryFlag(**kwargs)
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag
