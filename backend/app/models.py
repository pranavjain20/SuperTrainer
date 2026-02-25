import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# --- Enums ---


class TierEnum(str, enum.Enum):
    free = "free"
    pro = "pro"
    trainer_pro = "trainer_pro"


class ProcessingStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RiskLevelEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EntryTypeEnum(str, enum.Enum):
    exercise_card = "exercise_card"
    observation_card = "observation_card"


class MessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"


# --- Models ---


class Trainer(Base):
    __tablename__ = "trainers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    tier: Mapped[TierEnum] = mapped_column(Enum(TierEnum), default=TierEnum.free, nullable=False)
    supabase_user_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clients: Mapped[list["Client"]] = relationship(back_populates="trainer", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="trainer", cascade="all, delete-orphan")
    session_plans: Mapped[list["SessionPlan"]] = relationship(back_populates="trainer", cascade="all, delete-orphan")
    brain_conversations: Mapped[list["BrainConversation"]] = relationship(
        back_populates="trainer", cascade="all, delete-orphan"
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    birth_date: Mapped[date | None] = mapped_column(Date)
    training_start_date: Mapped[date | None] = mapped_column(Date)
    goals: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    injury_history: Mapped[str | None] = mapped_column(Text)
    preferred_weight_unit: Mapped[str | None] = mapped_column(String(10), default="kg")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trainer: Mapped["Trainer"] = relationship(back_populates="clients")
    sessions: Mapped[list["Session"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    session_entries: Mapped[list["SessionEntry"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    analysis: Mapped["ClientAnalysis | None"] = relationship(back_populates="client", uselist=False, cascade="all, delete-orphan")
    session_plans: Mapped[list["SessionPlan"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class SessionPlan(Base):
    __tablename__ = "session_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    plan_text: Mapped[str] = mapped_column(Text, nullable=False)
    plan_text_embedding = mapped_column(Vector(1536), nullable=True)
    planned_for_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="session_plans")
    trainer: Mapped["Trainer"] = relationship(back_populates="session_plans")
    sessions: Mapped[list["Session"]] = relationship(back_populates="plan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float)
    raw_transcript: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[ProcessingStatusEnum] = mapped_column(
        Enum(ProcessingStatusEnum), default=ProcessingStatusEnum.pending, nullable=False
    )
    trainer_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("session_plans.id", ondelete="SET NULL"))
    transcript_embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    trainer: Mapped["Trainer"] = relationship(back_populates="sessions")
    client: Mapped["Client"] = relationship(back_populates="sessions")
    plan: Mapped["SessionPlan | None"] = relationship(back_populates="sessions")
    session_entries: Mapped[list["SessionEntry"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class SessionEntry(Base):
    __tablename__ = "session_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    entry_type: Mapped[EntryTypeEnum] = mapped_column(Enum(EntryTypeEnum), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Exercise card fields (nullable — only populated for exercise_card entries)
    exercise_name: Mapped[str | None] = mapped_column(String(255))
    exercise_canonical: Mapped[str | None] = mapped_column(String(255))
    sets: Mapped[list | None] = mapped_column(JSONB)
    total_volume_kg: Mapped[float | None] = mapped_column(Float)
    form_notes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    form_notes_embedding = mapped_column(Vector(1536), nullable=True)
    cues_given: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    cue_effectiveness: Mapped[dict | None] = mapped_column(JSONB)

    # Observation card fields (nullable — only populated for observation_card entries)
    observation_text: Mapped[str | None] = mapped_column(Text)
    observation_embedding = mapped_column(Vector(1536), nullable=True)
    attached_to_set: Mapped[int | None] = mapped_column(Integer)
    flag_color: Mapped[str | None] = mapped_column(String(50))
    flag_reason: Mapped[str | None] = mapped_column(String(500))

    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="session_entries")
    client: Mapped["Client"] = relationship(back_populates="session_entries")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="session_entry")


class InjuryFlag(Base):
    __tablename__ = "injury_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    session_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("session_entries.id", ondelete="SET NULL"))
    body_part: Mapped[str] = mapped_column(String(100), nullable=False)
    pain_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    description: Mapped[str | None] = mapped_column(Text)
    first_occurrence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_occurrence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="injury_flags")
    session: Mapped["Session"] = relationship(back_populates="injury_flags")
    session_entry: Mapped["SessionEntry | None"] = relationship(back_populates="injury_flags")


class ClientAnalysis(Base):
    __tablename__ = "client_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_session_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avg_weight_increase_pct_per_week: Mapped[float | None] = mapped_column(Float)
    current_volume_trend: Mapped[str | None] = mapped_column(String(50))  # increasing/stable/decreasing
    injury_risk_score: Mapped[float | None] = mapped_column(Float)  # 0-100
    injury_risk_level: Mapped[RiskLevelEnum | None] = mapped_column(Enum(RiskLevelEnum))
    risk_factors: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    form_degradation_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    overtraining_indicators: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pain_pattern_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    client_score: Mapped[float | None] = mapped_column(Float)  # 0-100
    client_score_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    last_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped["Client"] = relationship(back_populates="analysis")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    category: Mapped[str | None] = mapped_column(String(100))
    primary_muscles: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    equipment: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    difficulty: Mapped[str | None] = mapped_column(String(50))
    common_errors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrainConversation(Base):
    __tablename__ = "brain_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    trainer: Mapped["Trainer"] = relationship(back_populates="brain_conversations")
    messages: Mapped[list["BrainMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class BrainMessage(Base):
    __tablename__ = "brain_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brain_conversations.id", ondelete="CASCADE"), nullable=False)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRoleEnum] = mapped_column(Enum(MessageRoleEnum), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["BrainConversation"] = relationship(back_populates="messages")
