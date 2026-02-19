import uuid
from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models import ProcessingStatusEnum, RiskLevelEnum, TierEnum

T = TypeVar("T")


# --- Generic Wrappers ---


class PaginationMeta(BaseModel):
    cursor: str | None = None
    limit: int = 20
    has_more: bool = False


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: dict = {}


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Trainer ---


class TrainerCreate(BaseModel):
    email: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    phone: str | None = None
    tier: TierEnum = TierEnum.free


class TrainerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    phone: str | None
    tier: TierEnum
    created_at: datetime
    last_login: datetime | None


# --- Client ---


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    training_start_date: date | None = None
    goals: list[str] | None = None
    injury_history: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    training_start_date: date | None = None
    goals: list[str] | None = None
    injury_history: str | None = None
    archived: bool | None = None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trainer_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    birth_date: date | None
    training_start_date: date | None
    goals: list[str] | None
    injury_history: str | None
    archived: bool
    created_at: datetime


class ClientListResponse(BaseModel):
    data: list[ClientResponse]
    meta: PaginationMeta = PaginationMeta()


# --- Session ---


class SessionCreate(BaseModel):
    client_id: uuid.UUID
    started_at: datetime


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trainer_id: uuid.UUID
    client_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
    audio_url: str | None
    audio_duration_seconds: float | None
    raw_transcript: str | None
    processing_status: ProcessingStatusEnum
    trainer_edited: bool
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    data: list[SessionResponse]
    meta: PaginationMeta = PaginationMeta()


# --- ExerciseLog ---


class ExerciseLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    client_id: uuid.UUID
    exercise_name: str
    exercise_canonical: str | None
    sets: dict | None
    total_volume_kg: float | None
    form_notes: list[str] | None
    cues_given: list[str] | None
    cue_effectiveness: dict | None
    performed_at: datetime | None
    created_at: datetime


# --- InjuryFlag ---


class InjuryFlagCreate(BaseModel):
    client_id: uuid.UUID
    session_id: uuid.UUID
    exercise_log_id: uuid.UUID | None = None
    body_part: str = Field(..., min_length=1)
    pain_level: int = Field(..., ge=1, le=10)
    description: str | None = None


class InjuryFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    session_id: uuid.UUID
    exercise_log_id: uuid.UUID | None
    body_part: str
    pain_level: int
    description: str | None
    first_occurrence: datetime | None
    last_occurrence: datetime | None
    occurrence_count: int
    resolved: bool
    resolved_at: datetime | None
    flagged_at: datetime
