import enum
import uuid
from datetime import date, datetime

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
    UniqueConstraint,
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


# --- Models ---


class Trainer(Base):
    __tablename__ = "trainers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    tier: Mapped[TierEnum] = mapped_column(Enum(TierEnum), default=TierEnum.free, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clients: Mapped[list["Client"]] = relationship(back_populates="trainer", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="trainer")


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
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trainer: Mapped["Trainer"] = relationship(back_populates="clients")
    sessions: Mapped[list["Session"]] = relationship(back_populates="client")
    exercise_logs: Mapped[list["ExerciseLog"]] = relationship(back_populates="client")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="client")
    analysis: Mapped["ClientAnalysis | None"] = relationship(back_populates="client", uselist=False)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trainers.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float)
    raw_transcript: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[ProcessingStatusEnum] = mapped_column(
        Enum(ProcessingStatusEnum), default=ProcessingStatusEnum.pending, nullable=False
    )
    trainer_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    trainer: Mapped["Trainer"] = relationship(back_populates="sessions")
    client: Mapped["Client"] = relationship(back_populates="sessions")
    exercise_logs: Mapped[list["ExerciseLog"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exercise_canonical: Mapped[str | None] = mapped_column(String(255))
    sets: Mapped[dict | None] = mapped_column(JSONB)
    total_volume_kg: Mapped[float | None] = mapped_column(Float)
    form_notes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    cues_given: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    cue_effectiveness: Mapped[dict | None] = mapped_column(JSONB)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="exercise_logs")
    client: Mapped["Client"] = relationship(back_populates="exercise_logs")
    injury_flags: Mapped[list["InjuryFlag"]] = relationship(back_populates="exercise_log")


class InjuryFlag(Base):
    __tablename__ = "injury_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    exercise_log_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("exercise_logs.id", ondelete="SET NULL"))
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
    exercise_log: Mapped["ExerciseLog | None"] = relationship(back_populates="injury_flags")


class ClientAnalysis(Base):
    __tablename__ = "client_analysis"
    __table_args__ = (UniqueConstraint("client_id"),)

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
