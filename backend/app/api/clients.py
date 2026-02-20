import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ClientCreate, ClientListResponse, ClientResponse, ClientUpdate,
    PaginationMeta, SessionListResponse, SessionResponse,
)
from app.services import client_service, session_service

router = APIRouter(prefix="/clients", tags=["clients"])

# Hardcoded trainer_id until auth is implemented (Week 10).
# Every endpoint will use get_current_trainer_id() so we only change one place later.
TEMP_TRAINER_ID: uuid.UUID | None = None


async def _get_trainer_id(db: AsyncSession) -> uuid.UUID:
    """Get the first trainer's ID. Replaced by auth in Week 10."""
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


@router.get("", response_model=ClientListResponse)
async def list_clients(
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    trainer_id = await _get_trainer_id(db)
    clients, has_more = await client_service.list_clients(
        db, trainer_id, cursor=cursor, limit=limit, include_archived=include_archived,
    )
    last_id = str(clients[-1].id) if clients else None
    return ClientListResponse(
        data=[ClientResponse.model_validate(c) for c in clients],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.post("", response_model=dict, status_code=201)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
):
    trainer_id = await _get_trainer_id(db)
    client = await client_service.create_client(db, trainer_id, **body.model_dump(exclude_unset=True))
    return {"data": ClientResponse.model_validate(client), "meta": {}}


@router.get("/{client_id}", response_model=dict)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"data": ClientResponse.model_validate(client), "meta": {}}


@router.patch("/{client_id}", response_model=dict)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = await client_service.update_client(db, client, **body.model_dump(exclude_unset=True))
    return {"data": ClientResponse.model_validate(updated), "meta": {}}


@router.patch("/{client_id}/archive", response_model=dict)
async def archive_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    archived = await client_service.archive_client(db, client)
    return {"data": ClientResponse.model_validate(archived), "meta": {}}


@router.get("/{client_id}/sessions", response_model=SessionListResponse)
async def list_client_sessions(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    client = await client_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    sessions, has_more = await session_service.list_sessions_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(sessions[-1].id) if sessions else None
    return SessionListResponse(
        data=[SessionResponse.model_validate(s) for s in sessions],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )
