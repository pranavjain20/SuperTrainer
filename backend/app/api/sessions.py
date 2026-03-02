import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_trainer_id, validate_client_ownership, validate_session_ownership
from app.database import get_db
from app.models import EntryTypeEnum, SessionPlan
from app.schemas import (
    DataResponse,
    PaginationMeta,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
    WorkoutClassificationResponse,
)
from app.services import entry_service, session_service
from app.services.workout_classifier import classify_workout

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    scheduled_for_date: date | None = Query(None, description="Filter by date (ISO format, e.g. 2026-02-25)"),
    tz: str = Query("UTC", description="IANA timezone (e.g. America/New_York) for date filtering"),
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    trainer_id = await get_trainer_id(db)
    sessions, has_more = await session_service.list_sessions_by_trainer(
        db, trainer_id, scheduled_for_date=scheduled_for_date, tz=tz, cursor=cursor, limit=limit,
    )
    last_id = str(sessions[-1].id) if sessions else None
    return SessionListResponse(
        data=[SessionResponse.model_validate(s) for s in sessions],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


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
    data = body.model_dump(exclude_unset=True)

    # Auto-compute duration when ending a session
    if "ended_at" in data and data["ended_at"] is not None and session.started_at:
        delta = data["ended_at"] - session.started_at
        data["duration_minutes"] = max(0, round(delta.total_seconds() / 60))

    # Validate plan_id ownership (same logic as create)
    if "plan_id" in data and data["plan_id"] is not None:
        plan = await db.get(SessionPlan, data["plan_id"])
        if plan is None or plan.trainer_id != session.trainer_id:
            raise HTTPException(status_code=404, detail="Session plan not found")
        if plan.client_id != session.client_id:
            raise HTTPException(status_code=422, detail="Plan does not belong to this client")

    updated = await session_service.update_session(db, session, **data)
    return {"data": SessionResponse.model_validate(updated), "meta": {}}


@router.post("/{session_id}/classify", response_model=DataResponse[WorkoutClassificationResponse])
async def classify_session_workout(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await validate_session_ownership(db, session_id)
    entries = await entry_service.list_entries_by_session(db, session_id)
    canonical_names = [
        e.exercise_canonical
        for e in entries
        if e.entry_type == EntryTypeEnum.exercise_card and e.exercise_canonical
    ]
    workout_type = classify_workout(canonical_names)
    return {
        "data": WorkoutClassificationResponse(workout_type=workout_type),
        "meta": {},
    }


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    session = await validate_session_ownership(db, session_id)
    await session_service.delete_session(db, session)
