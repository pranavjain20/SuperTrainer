import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InjuryFlag
from app.services.pagination import paginate


async def list_injury_flags_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[InjuryFlag], bool]:
    """Return (injury_flags, has_more) for a client, newest first."""
    query = select(InjuryFlag).where(InjuryFlag.client_id == client_id)
    return await paginate(db, query, InjuryFlag, InjuryFlag.flagged_at, cursor=cursor, limit=limit)


async def get_injury_flag(db: AsyncSession, flag_id: uuid.UUID) -> InjuryFlag | None:
    return await db.get(InjuryFlag, flag_id)


async def create_injury_flag(db: AsyncSession, **kwargs) -> InjuryFlag:
    flag = InjuryFlag(**kwargs)
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag


async def update_injury_flag(db: AsyncSession, flag: InjuryFlag, **kwargs) -> InjuryFlag:
    for key, value in kwargs.items():
        if value is not None:
            setattr(flag, key, value)
    await db.commit()
    await db.refresh(flag)
    return flag


async def delete_injury_flag(db: AsyncSession, flag: InjuryFlag) -> None:
    await db.delete(flag)
    await db.commit()
