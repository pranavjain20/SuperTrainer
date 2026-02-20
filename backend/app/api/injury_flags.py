import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    InjuryFlagCreate,
    InjuryFlagListResponse,
    InjuryFlagResponse,
    PaginationMeta,
)
from app.services import client_service, exercise_log_service, injury_flag_service, session_service

router = APIRouter(tags=["injury-flags"])


@router.get("/clients/{client_id}/injury-flags", response_model=InjuryFlagListResponse)
async def list_injury_flags_by_client(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    flags, has_more = await injury_flag_service.list_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(flags[-1].id) if flags else None
    return InjuryFlagListResponse(
        data=[InjuryFlagResponse.model_validate(f) for f in flags],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.post("/injury-flags", response_model=dict, status_code=201)
async def create_injury_flag(
    body: InjuryFlagCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify client exists
    client = await client_service.get_client(db, body.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Verify session exists
    session = await session_service.get_session(db, body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify session belongs to this client
    if session.client_id != body.client_id:
        raise HTTPException(status_code=422, detail="Session does not belong to this client")

    # Verify exercise_log_id exists and belongs to this session if provided
    if body.exercise_log_id is not None:
        exercise_log = await exercise_log_service.get_exercise_log(db, body.exercise_log_id)
        if exercise_log is None:
            raise HTTPException(status_code=404, detail="Exercise log not found")
        if exercise_log.session_id != body.session_id:
            raise HTTPException(status_code=422, detail="Exercise log does not belong to this session")

    flag = await injury_flag_service.create_injury_flag(db, **body.model_dump())
    return {"data": InjuryFlagResponse.model_validate(flag), "meta": {}}
