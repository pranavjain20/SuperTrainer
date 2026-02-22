import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import validate_client_ownership, validate_entry_ownership, validate_session_ownership
from app.database import get_db
from app.models import EntryTypeEnum
from app.schemas import (
    DataResponse,
    PaginationMeta,
    SessionEntryCreate,
    SessionEntryListResponse,
    SessionEntryResponse,
    SessionEntryUpdate,
)
from app.services import entry_service

router = APIRouter(tags=["entries"])


@router.post("/sessions/{session_id}/entries", response_model=DataResponse[SessionEntryResponse], status_code=201)
async def create_entry(
    session_id: uuid.UUID,
    body: SessionEntryCreate,
    db: AsyncSession = Depends(get_db),
):
    session = await validate_session_ownership(db, session_id)

    # Auto-calculate sequence_order if not provided
    data = body.model_dump(exclude_unset=True)
    if "sequence_order" not in data or data.get("sequence_order") is None:
        data["sequence_order"] = await entry_service.get_next_sequence_order(db, session_id)

    entry = await entry_service.create_entry(
        db, session_id=session_id, client_id=session.client_id, **data
    )
    return {"data": SessionEntryResponse.model_validate(entry), "meta": {}}


@router.get(
    "/sessions/{session_id}/entries", response_model=SessionEntryListResponse
)
async def list_entries_by_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await validate_session_ownership(db, session_id)
    entries = await entry_service.list_entries_by_session(db, session_id)
    return SessionEntryListResponse(
        data=[SessionEntryResponse.model_validate(e) for e in entries],
        meta=PaginationMeta(has_more=False),
    )


@router.get(
    "/clients/{client_id}/entries", response_model=SessionEntryListResponse
)
async def list_entries_by_client(
    client_id: uuid.UUID,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    await validate_client_ownership(db, client_id)
    entries, has_more = await entry_service.list_entries_by_client(
        db, client_id, cursor=cursor, limit=limit,
    )
    last_id = str(entries[-1].id) if entries else None
    return SessionEntryListResponse(
        data=[SessionEntryResponse.model_validate(e) for e in entries],
        meta=PaginationMeta(cursor=last_id, limit=limit, has_more=has_more),
    )


@router.get("/entries/{entry_id}", response_model=DataResponse[SessionEntryResponse])
async def get_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    entry = await validate_entry_ownership(db, entry_id)
    return {"data": SessionEntryResponse.model_validate(entry), "meta": {}}


@router.patch("/entries/{entry_id}", response_model=DataResponse[SessionEntryResponse])
async def update_entry(
    entry_id: uuid.UUID,
    body: SessionEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    entry = await validate_entry_ownership(db, entry_id)

    # Route-level cross-type validation: when entry_type is NOT in the payload,
    # the schema can't know the existing type — check it here against the DB entry.
    data = body.model_dump(exclude_unset=True)
    if "entry_type" not in data:
        _reject_cross_type_fields(entry.entry_type, data)

    updated = await entry_service.update_entry(db, entry, **data)
    return {"data": SessionEntryResponse.model_validate(updated), "meta": {}}


# Fields that belong exclusively to one entry type — mirrors the schema validator.
_OBSERVATION_ONLY = {"observation_text", "attached_to_set"}
_EXERCISE_ONLY = {"exercise_name", "sets"}


def _reject_cross_type_fields(actual_type: EntryTypeEnum, payload: dict) -> None:
    if actual_type == EntryTypeEnum.exercise_card:
        bad = _OBSERVATION_ONLY & payload.keys()
        if bad:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot set observation_card fields on exercise_card entry: {', '.join(sorted(bad))}",
            )
    elif actual_type == EntryTypeEnum.observation_card:
        bad = _EXERCISE_ONLY & payload.keys()
        if bad:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot set exercise_card fields on observation_card entry: {', '.join(sorted(bad))}",
            )


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    entry = await validate_entry_ownership(db, entry_id)
    await entry_service.delete_entry(db, entry)
