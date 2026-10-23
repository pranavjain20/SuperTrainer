import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_trainer_id
from app.database import get_db
from app.schemas import BrainAskRequest, BrainAskResponse, DataResponse
from app.services.brain import ask_brain

router = APIRouter(prefix="/brain", tags=["brain"])


@router.post("/ask", response_model=DataResponse[BrainAskResponse])
async def ask(body: BrainAskRequest, db: AsyncSession = Depends(get_db)):
    """Answer a trainer's question about their clients from their training data."""
    trainer_id = await get_trainer_id(db)
    try:
        answer = await ask_brain(db, trainer_id, body.question)
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail="The Brain could not answer right now") from e
    return {"data": BrainAskResponse(answer=answer), "meta": {}}
