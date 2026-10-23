import uuid
from datetime import date

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_trainer_id, validate_client_ownership, validate_session_ownership
from app.database import get_db
from app.models import SessionPlan
from app.schemas import (
    DataResponse,
    PaginationMeta,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionSummaryResponse,
    SessionUpdate,
)
from app.services import session_service
from app.services.session_summary import summarize_session

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
        data=await session_service.to_responses(db, sessions),
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
    return {"data": await session_service.to_response(db, session), "meta": {}}


@router.get("/{session_id}", response_model=DataResponse[SessionResponse])
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await validate_session_ownership(db, session_id)
    return {"data": await session_service.to_response(db, session), "meta": {}}


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
    return {"data": await session_service.to_response(db, updated), "meta": {}}


@router.post("/{session_id}/summary", response_model=DataResponse[SessionSummaryResponse])
async def summarize(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Claude's recap of a finished session, written on first request and stored.

    Editing an entry clears it (entry_service), so the next request rewrites it.
    A session with nothing recorded has no recap.
    """
    session = await validate_session_ownership(db, session_id)
    if session.ended_at is None:
        raise HTTPException(status_code=409, detail="Session has not ended yet")
    if session.ai_summary is None:
        try:
            session.ai_summary = await summarize_session(db, session)
        except anthropic.APIError as e:
            raise HTTPException(status_code=502, detail="Could not write the summary right now") from e
        await db.commit()
        await db.refresh(session)
    return {"data": SessionSummaryResponse(ai_summary=session.ai_summary), "meta": {}}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    session = await validate_session_ownership(db, session_id)
    await session_service.delete_session(db, session)
