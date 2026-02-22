import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import validate_client_ownership, validate_flag_ownership
from app.database import get_db
from app.models import SessionEntry
from app.schemas import (
    DataResponse,
    InjuryFlagCreate,
    InjuryFlagListResponse,
    InjuryFlagResponse,
    InjuryFlagUpdate,
    PaginationMeta,
)
from app.services import injury_flag_service, session_service

router = APIRouter(tags=["injury_flags"])


@router.get("/clients/{client_id}/injury-flags", response_model=InjuryFlagListResponse)
async def list_injury_flags_by_client(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    await validate_client_ownership(db, client_id)

    flags, has_more = await injury_flag_service.list_injury_flags_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(flags[-1].id) if flags else None
    return InjuryFlagListResponse(
        data=[InjuryFlagResponse.model_validate(f) for f in flags],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.post("/injury-flags", response_model=DataResponse[InjuryFlagResponse], status_code=201)
async def create_injury_flag(
    body: InjuryFlagCreate,
    db: AsyncSession = Depends(get_db),
):
    await validate_client_ownership(db, body.client_id)

    # Verify session exists
    session = await session_service.get_session(db, body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify session belongs to this client
    if session.client_id != body.client_id:
        raise HTTPException(status_code=422, detail="Session does not belong to this client")

    # Verify session_entry_id exists and belongs to this session if provided
    if body.session_entry_id is not None:
        entry = await db.get(SessionEntry, body.session_entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Session entry not found")
        if entry.session_id != body.session_id:
            raise HTTPException(status_code=422, detail="Session entry does not belong to this session")

    flag = await injury_flag_service.create_injury_flag(db, **body.model_dump())
    return {"data": InjuryFlagResponse.model_validate(flag), "meta": {}}


@router.get("/injury-flags/{flag_id}", response_model=DataResponse[InjuryFlagResponse])
async def get_injury_flag(
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    flag = await validate_flag_ownership(db, flag_id)
    return {"data": InjuryFlagResponse.model_validate(flag), "meta": {}}


@router.patch("/injury-flags/{flag_id}", response_model=DataResponse[InjuryFlagResponse])
async def update_injury_flag(
    flag_id: uuid.UUID,
    body: InjuryFlagUpdate,
    db: AsyncSession = Depends(get_db),
):
    flag = await validate_flag_ownership(db, flag_id)
    updated = await injury_flag_service.update_injury_flag(
        db, flag, **body.model_dump(exclude_unset=True)
    )
    return {"data": InjuryFlagResponse.model_validate(updated), "meta": {}}


@router.delete("/injury-flags/{flag_id}", status_code=204)
async def delete_injury_flag(
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    flag = await validate_flag_ownership(db, flag_id)
    await injury_flag_service.delete_injury_flag(db, flag)
