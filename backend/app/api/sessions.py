import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import PaginationMeta, SessionCreate, SessionListResponse, SessionResponse, SessionUpdate
from app.services import client_service, session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=dict, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify client exists
    client = await client_service.get_client(db, body.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    session = await session_service.create_session(
        db, trainer_id=client.trainer_id, **body.model_dump()
    )
    return {"data": SessionResponse.model_validate(session), "meta": {}}


@router.get("/{session_id}", response_model=dict)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"data": SessionResponse.model_validate(session), "meta": {}}


@router.patch("/{session_id}", response_model=dict)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = await session_service.update_session(db, session, **body.model_dump(exclude_unset=True))
    return {"data": SessionResponse.model_validate(updated), "meta": {}}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_service.delete_session(db, session)
