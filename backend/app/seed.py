"""Seed script: creates 1 trainer, 5 clients with sessions, exercise logs, and injury flags."""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models import (
    Client,
    ExerciseLog,
    InjuryFlag,
    ProcessingStatusEnum,
    Session,
    Trainer,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _utcnow() - timedelta(days=n)


async def seed(db: AsyncSession):
    # --- Trainer ---
    trainer = Trainer(
        email="coach@supertrainer.app",
        name="Coach Pranav",
        phone="+1-555-0100",
    )
    db.add(trainer)
    await db.flush()

    # --- 5 Clients ---
    clients_data = [
        {
            "name": "Sarah Chen",
            "email": "sarah.chen@email.com",
            "phone": "+1-555-0201",
            "birth_date": date(1996, 4, 15),
            "training_start_date": date(2025, 9, 1),
            "goals": ["lose weight", "build strength", "run a 5K"],
            "injury_history": "Mild lower back pain from desk job. No surgeries.",
        },
        {
            "name": "Marcus Johnson",
            "email": "marcus.j@email.com",
            "phone": "+1-555-0202",
            "birth_date": date(1990, 11, 3),
            "training_start_date": date(2025, 6, 15),
            "goals": ["powerlifting competition", "increase squat to 200kg"],
            "injury_history": "ACL repair right knee (2022). Cleared for full activity.",
        },
        {
            "name": "Aisha Patel",
            "email": "aisha.p@email.com",
            "phone": "+1-555-0203",
            "birth_date": date(1988, 7, 22),
            "training_start_date": date(2026, 1, 10),
            "goals": ["post-pregnancy recovery", "core strength", "general fitness"],
            "injury_history": "Diastasis recti. C-section 8 months ago.",
        },
        {
            "name": "Jake Morrison",
            "email": "jake.m@email.com",
            "phone": "+1-555-0204",
            "birth_date": date(2001, 2, 8),
            "training_start_date": date(2025, 11, 1),
            "goals": ["muscle gain", "improve posture"],
            "injury_history": "None.",
        },
        {
            "name": "Elena Vasquez",
            "email": "elena.v@email.com",
            "phone": "+1-555-0205",
            "birth_date": date(1975, 12, 30),
            "training_start_date": date(2025, 3, 1),
            "goals": ["bone density", "balance", "maintain independence"],
            "injury_history": "Osteoporosis diagnosis. Right hip replacement (2023). Chronic shoulder impingement left side.",
        },
    ]

    clients = []
    for data in clients_data:
        client = Client(trainer_id=trainer.id, **data)
        db.add(client)
        clients.append(client)
    await db.flush()

    # --- Sessions + Exercise Logs + Injury Flags ---

    # Sarah — 4 sessions, general strength, progressing well
    sarah = clients[0]
    for i, days in enumerate([21, 14, 7, 2]):
        session = Session(
            trainer_id=trainer.id,
            client_id=sarah.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=55),
            duration_minutes=55,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Sarah session {i+1} transcript placeholder",
        )
        db.add(session)
        await db.flush()

        weights = [40, 42.5, 45, 47.5]
        db.add(ExerciseLog(
            session_id=session.id, client_id=sarah.id,
            exercise_name="Barbell Back Squat", exercise_canonical="barbell_back_squat",
            sets=[{"set": j+1, "weight_kg": weights[i], "reps": 8, "rpe": 6+i} for j in range(4)],
            total_volume_kg=weights[i] * 8 * 4,
            form_notes=["depth improving" if i > 1 else "needs more depth"],
            cues_given=["chest up", "push knees out"],
        ))
        db.add(ExerciseLog(
            session_id=session.id, client_id=sarah.id,
            exercise_name="Romanian Deadlift", exercise_canonical="romanian_deadlift",
            sets=[{"set": j+1, "weight_kg": 30 + i*2.5, "reps": 10} for j in range(3)],
            total_volume_kg=(30 + i*2.5) * 10 * 3,
        ))

    # Marcus — 5 sessions, heavy lifter, knee concerns
    marcus = clients[1]
    for i, days in enumerate([28, 21, 14, 7, 3]):
        session = Session(
            trainer_id=trainer.id,
            client_id=marcus.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=75),
            duration_minutes=75,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Marcus session {i+1} transcript placeholder",
        )
        db.add(session)
        await db.flush()

        squat_weight = 140 + i * 5
        db.add(ExerciseLog(
            session_id=session.id, client_id=marcus.id,
            exercise_name="Barbell Back Squat", exercise_canonical="barbell_back_squat",
            sets=[{"set": j+1, "weight_kg": squat_weight, "reps": 5, "rpe": 7+i*0.5} for j in range(5)],
            total_volume_kg=squat_weight * 5 * 5,
            form_notes=["good depth", "slight knee valgus on last rep" if i >= 3 else "solid form"],
            cues_given=["brace harder", "push knees out"],
        ))
        db.add(ExerciseLog(
            session_id=session.id, client_id=marcus.id,
            exercise_name="Bench Press", exercise_canonical="barbell_bench_press",
            sets=[{"set": j+1, "weight_kg": 100 + i*2.5, "reps": 5} for j in range(5)],
            total_volume_kg=(100 + i*2.5) * 5 * 5,
        ))

    # Marcus knee pain flags (sessions 4 and 5)
    marcus_sessions = await db.execute(
        Session.__table__.select().where(Session.client_id == marcus.id).order_by(Session.started_at)
    )
    marcus_session_rows = marcus_sessions.fetchall()
    for row in marcus_session_rows[-2:]:
        db.add(InjuryFlag(
            client_id=marcus.id,
            session_id=row.id,
            body_part="right knee",
            pain_level=4 if row == marcus_session_rows[-2] else 5,
            description="Discomfort during heavy squats, around the lateral side",
            first_occurrence=_days_ago(7),
            last_occurrence=_days_ago(3),
            occurrence_count=2,
        ))

    # Aisha — 3 sessions, post-pregnancy, careful progression
    aisha = clients[2]
    for i, days in enumerate([14, 7, 1]):
        session = Session(
            trainer_id=trainer.id,
            client_id=aisha.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=45),
            duration_minutes=45,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Aisha session {i+1} transcript placeholder",
        )
        db.add(session)
        await db.flush()

        db.add(ExerciseLog(
            session_id=session.id, client_id=aisha.id,
            exercise_name="Goblet Squat", exercise_canonical="goblet_squat",
            sets=[{"set": j+1, "weight_kg": 8 + i*2, "reps": 12} for j in range(3)],
            total_volume_kg=(8 + i*2) * 12 * 3,
            form_notes=["good control"],
            cues_given=["engage core", "breathe out on exertion"],
        ))
        db.add(ExerciseLog(
            session_id=session.id, client_id=aisha.id,
            exercise_name="Dead Bug", exercise_canonical="dead_bug",
            sets=[{"set": j+1, "reps": 10, "duration_seconds": 30} for j in range(3)],
            form_notes=["maintaining neutral spine well"],
        ))

    # Jake — 3 sessions, beginner, fast progress
    jake = clients[3]
    for i, days in enumerate([10, 5, 1]):
        session = Session(
            trainer_id=trainer.id,
            client_id=jake.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=60),
            duration_minutes=60,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Jake session {i+1} transcript placeholder",
        )
        db.add(session)
        await db.flush()

        db.add(ExerciseLog(
            session_id=session.id, client_id=jake.id,
            exercise_name="Barbell Bench Press", exercise_canonical="barbell_bench_press",
            sets=[{"set": j+1, "weight_kg": 40 + i*5, "reps": 8} for j in range(4)],
            total_volume_kg=(40 + i*5) * 8 * 4,
            form_notes=["elbows flaring" if i == 0 else "better tuck"],
            cues_given=["tuck elbows", "leg drive"],
        ))
        db.add(ExerciseLog(
            session_id=session.id, client_id=jake.id,
            exercise_name="Lat Pulldown", exercise_canonical="lat_pulldown",
            sets=[{"set": j+1, "weight_kg": 45 + i*5, "reps": 10} for j in range(3)],
            total_volume_kg=(45 + i*5) * 10 * 3,
        ))

    # Elena — 5 sessions, elderly, careful with shoulder
    elena = clients[4]
    for i, days in enumerate([35, 28, 21, 14, 7]):
        session = Session(
            trainer_id=trainer.id,
            client_id=elena.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=40),
            duration_minutes=40,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Elena session {i+1} transcript placeholder",
        )
        db.add(session)
        await db.flush()

        db.add(ExerciseLog(
            session_id=session.id, client_id=elena.id,
            exercise_name="Leg Press", exercise_canonical="leg_press",
            sets=[{"set": j+1, "weight_kg": 40 + i*2.5, "reps": 12} for j in range(3)],
            total_volume_kg=(40 + i*2.5) * 12 * 3,
            form_notes=["full ROM", "no hip pain"],
        ))
        db.add(ExerciseLog(
            session_id=session.id, client_id=elena.id,
            exercise_name="Seated Row", exercise_canonical="seated_row",
            sets=[{"set": j+1, "weight_kg": 20, "reps": 12} for j in range(3)],
            total_volume_kg=20 * 12 * 3,
            form_notes=["avoiding overhead due to shoulder"],
        ))

    # Elena shoulder pain flag
    elena_sessions = await db.execute(
        Session.__table__.select().where(Session.client_id == elena.id).order_by(Session.started_at)
    )
    elena_session_rows = elena_sessions.fetchall()
    db.add(InjuryFlag(
        client_id=elena.id,
        session_id=elena_session_rows[2].id,
        body_part="left shoulder",
        pain_level=3,
        description="Impingement flare during lateral raises, avoided overhead work",
        first_occurrence=_days_ago(60),
        last_occurrence=_days_ago(21),
        occurrence_count=4,
    ))

    await db.commit()
    print(f"Seeded: 1 trainer, 5 clients, 20 sessions, exercise logs, and injury flags")


async def main():
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
