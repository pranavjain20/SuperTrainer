import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, InjuryFlag, Session, SessionEntry, SessionPlan
from app.services import client_service, entry_service, injury_flag_service, plan_service, session_service

# Hardcoded trainer_id until auth is implemented (Phase 4).
# Every endpoint calls get_trainer_id() so we only change one place later.
TEMP_TRAINER_ID: uuid.UUID | None = None


async def get_trainer_id(db: AsyncSession) -> uuid.UUID:
    """Get the first trainer's ID. Replaced by auth in Phase 4."""
    global TEMP_TRAINER_ID
    if TEMP_TRAINER_ID is None:
        from sqlalchemy import select
        from app.models import Trainer
        result = await db.execute(select(Trainer).limit(1))
        trainer = result.scalar_one_or_none()
        if trainer is None:
            raise HTTPException(status_code=500, detail="No trainer found. Run the seed script first.")
        TEMP_TRAINER_ID = trainer.id
    return TEMP_TRAINER_ID


async def validate_client_ownership(
    db: AsyncSession, client_id: uuid.UUID,
) -> Client:
    """Return client if it exists and belongs to the current trainer. Raise 404 otherwise."""
    trainer_id = await get_trainer_id(db)
    client = await client_service.get_client(db, client_id)
    if client is None or client.trainer_id != trainer_id:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


async def validate_session_ownership(
    db: AsyncSession, session_id: uuid.UUID,
) -> Session:
    """Return session if it exists and belongs to the current trainer. Raise 404 otherwise."""
    trainer_id = await get_trainer_id(db)
    session = await session_service.get_session(db, session_id)
    if session is None or session.trainer_id != trainer_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def validate_entry_ownership(
    db: AsyncSession, entry_id: uuid.UUID,
) -> SessionEntry:
    """Return entry if it exists and belongs to the current trainer (via client). Raise 404 otherwise."""
    entry = await entry_service.get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    await validate_client_ownership(db, entry.client_id)
    return entry


async def validate_plan_ownership(
    db: AsyncSession, plan_id: uuid.UUID,
) -> SessionPlan:
    """Return plan if it exists and belongs to the current trainer. Raise 404 otherwise."""
    trainer_id = await get_trainer_id(db)
    plan = await plan_service.get_plan(db, plan_id)
    if plan is None or plan.trainer_id != trainer_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


async def validate_flag_ownership(
    db: AsyncSession, flag_id: uuid.UUID,
) -> InjuryFlag:
    """Return flag if it exists and its client belongs to the current trainer. Raise 404 otherwise."""
    flag = await injury_flag_service.get_injury_flag(db, flag_id)
    if flag is None:
        raise HTTPException(status_code=404, detail="Injury flag not found")
    await validate_client_ownership(db, flag.client_id)
    return flag
