import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_trainer_id, validate_client_ownership, validate_plan_ownership
from app.database import get_db
from app.schemas import (
    DataResponse,
    PaginationMeta,
    SessionPlanCreate,
    SessionPlanListResponse,
    SessionPlanResponse,
    SessionPlanUpdate,
)
from app.services import plan_service

router = APIRouter(tags=["plans"])


@router.post("/plans", response_model=DataResponse[SessionPlanResponse], status_code=201)
async def create_plan(
    body: SessionPlanCreate,
    db: AsyncSession = Depends(get_db),
):
    trainer_id = await get_trainer_id(db)
    await validate_client_ownership(db, body.client_id)

    plan = await plan_service.create_plan(
        db, trainer_id=trainer_id, **body.model_dump()
    )
    return {"data": SessionPlanResponse.model_validate(plan), "meta": {}}


@router.get("/clients/{client_id}/plans", response_model=SessionPlanListResponse)
async def list_plans_by_client(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    await validate_client_ownership(db, client_id)
    plans, has_more = await plan_service.list_plans_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(plans[-1].id) if plans else None
    return SessionPlanListResponse(
        data=[SessionPlanResponse.model_validate(p) for p in plans],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.get("/plans/{plan_id}", response_model=DataResponse[SessionPlanResponse])
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    plan = await validate_plan_ownership(db, plan_id)
    return {"data": SessionPlanResponse.model_validate(plan), "meta": {}}


@router.patch("/plans/{plan_id}", response_model=DataResponse[SessionPlanResponse])
async def update_plan(
    plan_id: uuid.UUID,
    body: SessionPlanUpdate,
    db: AsyncSession = Depends(get_db),
):
    plan = await validate_plan_ownership(db, plan_id)
    updated = await plan_service.update_plan(
        db, plan, **body.model_dump(exclude_unset=True)
    )
    return {"data": SessionPlanResponse.model_validate(updated), "meta": {}}


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    plan = await validate_plan_ownership(db, plan_id)
    await plan_service.delete_plan(db, plan)
