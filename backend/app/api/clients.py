import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_trainer_id, validate_client_ownership
from app.database import get_db
from app.schemas import (
    ClientCreate, ClientListResponse, ClientResponse, ClientUpdate,
    DataResponse, PaginationMeta, SessionListResponse, SessionResponse,
)
from app.services import client_service, session_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
async def list_clients(
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    trainer_id = await get_trainer_id(db)
    clients, has_more = await client_service.list_clients(
        db, trainer_id, cursor=cursor, limit=limit, include_archived=include_archived,
    )
    last_id = str(clients[-1].id) if clients else None
    return ClientListResponse(
        data=[ClientResponse.model_validate(c) for c in clients],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.post("", response_model=DataResponse[ClientResponse], status_code=201)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
):
    trainer_id = await get_trainer_id(db)
    client = await client_service.create_client(db, trainer_id, **body.model_dump(exclude_unset=True))
    return {"data": ClientResponse.model_validate(client), "meta": {}}


@router.get("/{client_id}", response_model=DataResponse[ClientResponse])
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    client = await validate_client_ownership(db, client_id)
    return {"data": ClientResponse.model_validate(client), "meta": {}}


@router.patch("/{client_id}", response_model=DataResponse[ClientResponse])
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
):
    client = await validate_client_ownership(db, client_id)
    updated = await client_service.update_client(db, client, **body.model_dump(exclude_unset=True))
    return {"data": ClientResponse.model_validate(updated), "meta": {}}


@router.patch("/{client_id}/archive", response_model=DataResponse[ClientResponse])
async def archive_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    client = await validate_client_ownership(db, client_id)
    archived = await client_service.archive_client(db, client)
    return {"data": ClientResponse.model_validate(archived), "meta": {}}


@router.get("/{client_id}/sessions", response_model=SessionListResponse)
async def list_client_sessions(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    await validate_client_ownership(db, client_id)
    sessions, has_more = await session_service.list_sessions_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(sessions[-1].id) if sessions else None
    return SessionListResponse(
        data=[SessionResponse.model_validate(s) for s in sessions],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )
