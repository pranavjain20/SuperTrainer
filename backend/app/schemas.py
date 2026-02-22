import uuid
from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    EntryTypeEnum,
    MessageRoleEnum,
    ProcessingStatusEnum,
    RiskLevelEnum,
    TierEnum,
)

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
    supabase_user_id: str | None
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
    name: str | None = Field(None, min_length=1)
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
    scheduled_for: datetime | None = None
    plan_id: uuid.UUID | None = None


class SessionUpdate(BaseModel):
    ended_at: datetime | None = None
    scheduled_for: datetime | None = None
    duration_minutes: int | None = Field(None, ge=0)
    raw_transcript: str | None = None
    processing_status: ProcessingStatusEnum | None = None
    trainer_edited: bool | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trainer_id: uuid.UUID
    client_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    scheduled_for: datetime | None
    duration_minutes: int | None
    audio_url: str | None
    audio_duration_seconds: float | None
    raw_transcript: str | None
    processing_status: ProcessingStatusEnum
    trainer_edited: bool
    plan_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    data: list[SessionResponse]
    meta: PaginationMeta = PaginationMeta()


# --- SessionEntry ---


class SessionEntryCreate(BaseModel):
    entry_type: EntryTypeEnum
    sequence_order: int | None = Field(None, ge=1)

    # Exercise card fields
    exercise_name: str | None = Field(None, min_length=1)
    exercise_canonical: str | None = Field(None, min_length=1)
    sets: list[dict] | None = None
    total_volume_kg: float | None = Field(None, ge=0)
    form_notes: list[str] | None = None
    cues_given: list[str] | None = None
    cue_effectiveness: dict | None = None

    # Observation card fields
    observation_text: str | None = None
    attached_to_set: int | None = None
    flag_color: str | None = None
    flag_reason: str | None = None

    performed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_entry_type_fields(self):
        if self.entry_type == EntryTypeEnum.exercise_card:
            if not self.exercise_name:
                raise ValueError("exercise_name is required for exercise_card entries")
            if self.observation_text is not None:
                raise ValueError("observation_text must be None for exercise_card entries")
            if self.attached_to_set is not None:
                raise ValueError("attached_to_set must be None for exercise_card entries")
        elif self.entry_type == EntryTypeEnum.observation_card:
            if not self.observation_text:
                raise ValueError("observation_text is required for observation_card entries")
            if self.exercise_name is not None:
                raise ValueError("exercise_name must be None for observation_card entries")
            if self.sets is not None:
                raise ValueError("sets must be None for observation_card entries")
        return self


class SessionEntryUpdate(BaseModel):
    entry_type: EntryTypeEnum | None = None
    sequence_order: int | None = Field(None, ge=1)

    # Exercise card fields
    exercise_name: str | None = Field(None, min_length=1)
    exercise_canonical: str | None = Field(None, min_length=1)
    sets: list[dict] | None = None
    total_volume_kg: float | None = Field(None, ge=0)
    form_notes: list[str] | None = None
    cues_given: list[str] | None = None
    cue_effectiveness: dict | None = None

    # Observation card fields
    observation_text: str | None = None
    attached_to_set: int | None = None
    flag_color: str | None = None
    flag_reason: str | None = None

    performed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_entry_type_fields(self):
        """Prevent cross-type field contamination on update.

        Only validates when entry_type is explicitly provided in the update.
        If entry_type is None (not being changed), skip validation since
        we can't know the current type from the schema alone.
        """
        if self.entry_type is None:
            return self
        if self.entry_type == EntryTypeEnum.exercise_card:
            if self.observation_text is not None:
                raise ValueError("observation_text must be None for exercise_card entries")
            if self.attached_to_set is not None:
                raise ValueError("attached_to_set must be None for exercise_card entries")
        elif self.entry_type == EntryTypeEnum.observation_card:
            if self.exercise_name is not None:
                raise ValueError("exercise_name must be None for observation_card entries")
            if self.sets is not None:
                raise ValueError("sets must be None for observation_card entries")
        return self


class SessionEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    client_id: uuid.UUID
    entry_type: EntryTypeEnum
    sequence_order: int
    exercise_name: str | None
    exercise_canonical: str | None
    sets: list[dict] | None
    total_volume_kg: float | None
    form_notes: list[str] | None
    cues_given: list[str] | None
    cue_effectiveness: dict | None
    observation_text: str | None
    attached_to_set: int | None
    flag_color: str | None
    flag_reason: str | None
    performed_at: datetime | None
    created_at: datetime


class SessionEntryListResponse(BaseModel):
    data: list[SessionEntryResponse]
    meta: PaginationMeta = PaginationMeta()


# --- SessionPlan ---


class SessionPlanCreate(BaseModel):
    client_id: uuid.UUID
    plan_text: str = Field(..., min_length=1)
    planned_for_date: date | None = None


class SessionPlanUpdate(BaseModel):
    plan_text: str | None = Field(None, min_length=1)
    planned_for_date: date | None = None


class SessionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    trainer_id: uuid.UUID
    plan_text: str
    planned_for_date: date | None
    created_at: datetime


class SessionPlanListResponse(BaseModel):
    data: list[SessionPlanResponse]
    meta: PaginationMeta = PaginationMeta()


# --- InjuryFlag ---


class InjuryFlagCreate(BaseModel):
    client_id: uuid.UUID
    session_id: uuid.UUID
    session_entry_id: uuid.UUID | None = None
    body_part: str = Field(..., min_length=1)
    pain_level: int = Field(..., ge=1, le=10)
    description: str | None = None


class InjuryFlagUpdate(BaseModel):
    body_part: str | None = Field(None, min_length=1)
    pain_level: int | None = Field(None, ge=1, le=10)
    description: str | None = None
    resolved: bool | None = None
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_resolved_at_requires_resolved(self):
        if self.resolved_at is not None and self.resolved is not True:
            raise ValueError("resolved_at requires resolved=true")
        return self


class InjuryFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    session_id: uuid.UUID
    session_entry_id: uuid.UUID | None
    body_part: str
    pain_level: int
    description: str | None
    first_occurrence: datetime | None
    last_occurrence: datetime | None
    occurrence_count: int
    resolved: bool
    resolved_at: datetime | None
    flagged_at: datetime


class InjuryFlagListResponse(BaseModel):
    data: list[InjuryFlagResponse]
    meta: PaginationMeta = PaginationMeta()


# --- ClientAnalysis ---


class ClientAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    total_sessions: int
    last_session_date: datetime | None
    avg_weight_increase_pct_per_week: float | None
    current_volume_trend: str | None
    injury_risk_score: float | None
    injury_risk_level: RiskLevelEnum | None
    risk_factors: list[str] | None
    form_degradation_detected: bool
    overtraining_indicators: bool
    pain_pattern_detected: bool
    client_score: float | None
    client_score_breakdown: dict | None
    last_computed_at: datetime | None


# --- Exercise ---


class ExerciseCreate(BaseModel):
    canonical_name: str = Field(..., min_length=1)
    aliases: list[str] | None = None
    category: str | None = None
    primary_muscles: list[str] | None = None
    equipment: list[str] | None = None
    difficulty: str | None = None
    common_errors: dict | None = None


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_name: str
    aliases: list[str] | None
    category: str | None
    primary_muscles: list[str] | None
    equipment: list[str] | None
    difficulty: str | None
    common_errors: dict | None
    created_at: datetime


# --- BrainConversation ---


class BrainConversationCreate(BaseModel):
    title: str | None = None


class BrainConversationUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)


class BrainConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trainer_id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class BrainConversationListResponse(BaseModel):
    data: list[BrainConversationResponse]
    meta: PaginationMeta = PaginationMeta()


# --- BrainMessage ---


class BrainMessageCreate(BaseModel):
    role: MessageRoleEnum
    content: str = Field(..., min_length=1)


class BrainMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    trainer_id: uuid.UUID
    role: MessageRoleEnum
    content: str
    created_at: datetime
