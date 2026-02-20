import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ExerciseLogCreate,
    ExerciseLogListResponse,
    ExerciseLogResponse,
    PaginationMeta,
)
from app.services import client_service, exercise_log_service, session_service

router = APIRouter(tags=["exercise-logs"])


@router.get("/sessions/{session_id}/exercise-logs", response_model=ExerciseLogListResponse)
async def list_exercise_logs_by_session(
    session_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    logs, has_more = await exercise_log_service.list_by_session(
        db, session_id, cursor=cursor, limit=limit,
    )
    last_id = str(logs[-1].id) if logs else None
    return ExerciseLogListResponse(
        data=[ExerciseLogResponse.model_validate(log) for log in logs],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.get("/clients/{client_id}/exercise-logs", response_model=ExerciseLogListResponse)
async def list_exercise_logs_by_client(
    client_id: uuid.UUID,
    exercise_name: str | None = None,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    logs, has_more = await exercise_log_service.list_by_client(
        db, client_id, exercise_name=exercise_name, cursor=cursor, limit=limit,
    )
    last_id = str(logs[-1].id) if logs else None
    return ExerciseLogListResponse(
        data=[ExerciseLogResponse.model_validate(log) for log in logs],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.post("/exercise-logs", response_model=dict, status_code=201)
async def create_exercise_log(
    body: ExerciseLogCreate,
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    log = await exercise_log_service.create_exercise_log(
        db, client_id=session.client_id, **body.model_dump(),
    )
    return {"data": ExerciseLogResponse.model_validate(log), "meta": {}}
