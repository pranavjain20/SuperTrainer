import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionPlan
from app.services.pagination import paginate


async def get_plan(db: AsyncSession, plan_id: uuid.UUID) -> SessionPlan | None:
    return await db.get(SessionPlan, plan_id)


async def create_plan(db: AsyncSession, trainer_id: uuid.UUID, **kwargs) -> SessionPlan:
    plan = SessionPlan(trainer_id=trainer_id, **kwargs)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def list_plans_by_client(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list[SessionPlan], bool]:
    """Return (plans, has_more) for a client, newest first."""
    query = select(SessionPlan).where(SessionPlan.client_id == client_id)
    return await paginate(db, query, SessionPlan, SessionPlan.created_at, cursor=cursor, limit=limit)


async def update_plan(db: AsyncSession, plan: SessionPlan, **kwargs) -> SessionPlan:
    # Unlike other services, plans support nulling planned_for_date.
    # Safe because the router uses exclude_unset=True — only explicitly sent fields arrive here.
    for key, value in kwargs.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_plan(db: AsyncSession, plan: SessionPlan) -> None:
    await db.delete(plan)
    await db.commit()
