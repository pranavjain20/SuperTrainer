import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import validate_client_ownership, validate_session_ownership
from app.database import get_db
from app.models import SessionPlan
from app.schemas import DataResponse, PaginationMeta, SessionCreate, SessionListResponse, SessionResponse, SessionUpdate
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=DataResponse[SessionResponse], status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    client = await validate_client_ownership(db, body.client_id)

    # Verify plan_id exists, belongs to this trainer, and matches the client
    if body.plan_id is not None:
        plan = await db.get(SessionPlan, body.plan_id)
        if plan is None or plan.trainer_id != client.trainer_id:
            raise HTTPException(status_code=404, detail="Session plan not found")
        if plan.client_id != body.client_id:
            raise HTTPException(status_code=422, detail="Plan does not belong to this client")

    session = await session_service.create_session(
        db, trainer_id=client.trainer_id, **body.model_dump()
    )
    return {"data": SessionResponse.model_validate(session), "meta": {}}


@router.get("/{session_id}", response_model=DataResponse[SessionResponse])
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await validate_session_ownership(db, session_id)
    return {"data": SessionResponse.model_validate(session), "meta": {}}


@router.patch("/{session_id}", response_model=DataResponse[SessionResponse])
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    session = await validate_session_ownership(db, session_id)
    updated = await session_service.update_session(db, session, **body.model_dump(exclude_unset=True))
    return {"data": SessionResponse.model_validate(updated), "meta": {}}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    session = await validate_session_ownership(db, session_id)
    await session_service.delete_session(db, session)
