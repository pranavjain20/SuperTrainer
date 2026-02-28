"""Seed script: creates 1 trainer, 5 clients with realistic session data.

Idempotent — truncates all tables before seeding.
Run: python -m app.seed
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import (
    Client,
    EntryTypeEnum,
    Exercise,
    InjuryFlag,
    ProcessingStatusEnum,
    Session,
    SessionEntry,
    SessionPlan,
    Trainer,
)
from app.services.transcription import load_exercise_db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _utcnow() - timedelta(days=n)


def _compute_volume(sets: list[dict]) -> float:
    """Sum weight_kg * reps across all sets."""
    return sum(s.get("weight_kg", 0) * s.get("reps", 0) for s in sets)


# ---------------------------------------------------------------------------
# Exercise table seed
# ---------------------------------------------------------------------------

def _seed_exercises(db: AsyncSession) -> list[Exercise]:
    """Seed exercises from the canonical exercise_db.json file."""
    exercises_data = load_exercise_db()

    # Only pass fields that the Exercise model actually has as columns.
    # This lets the JSON carry extra data (secondary_muscles, research_notes)
    # without breaking the seed.
    from sqlalchemy import inspect as sa_inspect

    model_columns = {c.key for c in sa_inspect(Exercise).mapper.column_attrs}
    auto_fields = {"id", "created_at"}  # set by DB, not from JSON
    accepted_fields = model_columns - auto_fields

    exercises = []
    for data in exercises_data:
        filtered = {k: v for k, v in data.items() if k in accepted_fields}
        ex = Exercise(**filtered)
        db.add(ex)
        exercises.append(ex)
    return exercises


# ---------------------------------------------------------------------------
# Per-client seed helpers
# ---------------------------------------------------------------------------

def _seed_sarah(
    db: AsyncSession, trainer: Trainer, client: Client,
) -> tuple[list[Session], list[SessionEntry]]:
    """Sarah Chen — 1 session, 4 exercises + 2 observations (before and between)."""
    sessions = []
    entries = []

    session = Session(
        trainer_id=trainer.id,
        client_id=client.id,
        started_at=_days_ago(3),
        ended_at=_days_ago(3) + timedelta(minutes=50),
        duration_minutes=50,
        processing_status=ProcessingStatusEnum.completed,
        raw_transcript="Sarah assessment session — movement screening, baseline measurements",
    )
    db.add(session)
    sessions.append(session)

    # Pre-session observation: trainer asks how Sarah is feeling
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.observation_card,
        sequence_order=1,
        observation_text="Sarah hasn't slept much, energy levels below baseline.",
        flag_color="yellow",
        flag_reason="Low Energy",
    ))

    # Goblet Squat — per-set notes where relevant
    goblet_sets = [
        {"set": 1, "weight_kg": 8.0, "reps": 8, "rpe": 5},
        {"set": 2, "weight_kg": 8.0, "reps": 8, "rpe": 6, "notes": "left glute felt tight"},
        {"set": 3, "weight_kg": 8.0, "reps": 8, "rpe": 6},
    ]
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=2,
        exercise_name="Goblet Squat",
        exercise_canonical="goblet_squat",
        sets=goblet_sets,
        total_volume_kg=_compute_volume(goblet_sets),
    ))

    # Romanian Deadlift — per-set notes
    hinge_sets = [
        {"set": 1, "weight_kg": 0, "reps": 10},
        {"set": 2, "weight_kg": 0, "reps": 10, "notes": "rounding at bottom of rep"},
        {"set": 3, "weight_kg": 0, "reps": 8, "notes": "cut short, felt dizzy"},
    ]
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=3,
        exercise_name="Romanian Deadlift",
        exercise_canonical="romanian_deadlift",
        sets=hinge_sets,
        total_volume_kg=0,
    ))

    # Observation between exercises: energy dropping
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.observation_card,
        sequence_order=4,
        observation_text=(
            "After goblet squat and Romanian deadlift, "
            "Sarah reported energy levels even lower. Slowing pace for remaining exercises."
        ),
        flag_color="yellow",
        flag_reason="Fatigue Warning",
    ))

    # Push-Up
    pushup_sets = [
        {"set": 1, "reps": 8, "rpe": 7},
        {"set": 2, "reps": 6, "rpe": 8, "notes": "stopped early, arms shaking"},
        {"set": 3, "reps": 5, "rpe": 9},
    ]
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=5,
        exercise_name="Push-Up",
        exercise_canonical="push_up",
        sets=pushup_sets,
        total_volume_kg=0,
    ))

    # Plank
    plank_sets = [
        {"set": 1, "duration_seconds": 30},
        {"set": 2, "duration_seconds": 25, "notes": "hip sagging at 20s"},
        {"set": 3, "duration_seconds": 20, "notes": "cut short, fatigued"},
    ]
    entries.append(SessionEntry(
        session_id=None,
        client_id=client.id,
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=6,
        exercise_name="Plank",
        exercise_canonical="plank",
        sets=plank_sets,
        total_volume_kg=0,
    ))

    return sessions, entries


def _seed_marcus(
    db: AsyncSession, trainer: Trainer, client: Client,
) -> tuple[list[Session], list[SessionEntry], list[InjuryFlag]]:
    """Marcus Johnson — 3 sessions, powerlifter. Weight progression + 1 injury flag."""
    sessions = []
    entries = []
    injuries = []

    session_days = [21, 14, 7]
    squat_weights = [140.0, 145.0, 150.0]
    bench_weights = [100.0, 102.5, 105.0]
    deadlift_weights = [180.0, 185.0, 190.0]

    for i, days in enumerate(session_days):
        session = Session(
            trainer_id=trainer.id,
            client_id=client.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=75),
            duration_minutes=75,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Marcus session {i + 1} — heavy compound day",
        )
        db.add(session)
        sessions.append(session)

        order = 1

        # Squat
        squat_sets = [{"set": j, "weight_kg": squat_weights[i], "reps": 5, "rpe": 7 + i * 0.5} for j in range(1, 6)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Barbell Back Squat",
            exercise_canonical="barbell_back_squat",
            sets=squat_sets,
            total_volume_kg=_compute_volume(squat_sets),
            form_notes=["good depth"] if i < 2 else ["slight knee valgus on last rep"],
            cues_given=["brace harder", "push knees out"],
        ))
        order += 1

        # Bench
        bench_sets = [{"set": j, "weight_kg": bench_weights[i], "reps": 5, "rpe": 7 + i * 0.5} for j in range(1, 6)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Barbell Bench Press",
            exercise_canonical="barbell_bench_press",
            sets=bench_sets,
            total_volume_kg=_compute_volume(bench_sets),
            form_notes=["solid arch", "good leg drive"],
            cues_given=["tuck elbows", "drive feet"],
        ))
        order += 1

        # Deadlift
        dl_sets = [{"set": j, "weight_kg": deadlift_weights[i], "reps": 3, "rpe": 8 + i * 0.5} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Deadlift",
            exercise_canonical="deadlift",
            sets=dl_sets,
            total_volume_kg=_compute_volume(dl_sets),
            form_notes=["strong lockout"] if i < 2 else ["grip starting to fatigue"],
            cues_given=["wedge into the bar", "push the floor away"],
        ))
        order += 1

        # RDL accessory
        rdl_sets = [{"set": j, "weight_kg": 80 + i * 5, "reps": 8} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Romanian Deadlift",
            exercise_canonical="romanian_deadlift",
            sets=rdl_sets,
            total_volume_kg=_compute_volume(rdl_sets),
        ))
        order += 1

        # Observation card on session 2
        if i == 1:
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.observation_card,
                sequence_order=order,
                observation_text=(
                    "Weight is progressing well across all lifts. "
                    "Squat depth consistent. Watch right knee tracking "
                    "as load increases — history of ACL repair."
                ),
            ))

    # Injury flag on session 3 — right knee discomfort
    injuries.append(InjuryFlag(
        client_id=client.id,
        session_id=None,  # linked after flush
        body_part="right knee",
        pain_level=4,
        description="Discomfort during heavy squats at 150kg, lateral side. History of ACL repair.",
        first_occurrence=_days_ago(7),
        last_occurrence=_days_ago(7),
        occurrence_count=1,
    ))

    return sessions, entries, injuries


def _seed_aisha(
    db: AsyncSession, trainer: Trainer, client: Client,
) -> tuple[list[Session], list[SessionEntry], list[SessionPlan]]:
    """Aisha Patel — 5 sessions, post-pregnancy recovery. 1 session plan."""
    sessions = []
    entries = []
    plans = []

    # Plan created before sessions
    plan = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Focus on core reconnection and hip stability. "
            "3x10 dead bugs (strict form), 3x8 goblet squats progressing from 8kg to 10kg "
            "if last session felt controlled. Add band walks if energy allows. "
            "Watch for diastasis symptoms — stop any exercise that causes doming."
        ),
        planned_for_date=_days_ago(10).date(),
    )
    db.add(plan)
    plans.append(plan)

    session_days = [28, 21, 14, 7, 2]
    goblet_weights = [8.0, 8.0, 10.0, 10.0, 12.0]

    for i, days in enumerate(session_days):
        session = Session(
            trainer_id=trainer.id,
            client_id=client.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=45),
            duration_minutes=45,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Aisha session {i + 1} — post-natal recovery",
            plan_id=None,  # linked to plan for sessions 3+ (after plan was created)
        )
        db.add(session)
        sessions.append(session)

        order = 1

        # Goblet squat
        gs_sets = [{"set": j, "weight_kg": goblet_weights[i], "reps": 10, "rpe": 5 + i * 0.5} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Goblet Squat",
            exercise_canonical="goblet_squat",
            sets=gs_sets,
            total_volume_kg=_compute_volume(gs_sets),
            form_notes=["good control", "no doming observed"],
            cues_given=["engage core", "breathe out on exertion"],
        ))
        order += 1

        # Dead bug
        db_sets = [{"set": j, "reps": 10, "duration_seconds": 30} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Dead Bug",
            exercise_canonical="dead_bug",
            sets=db_sets,
            total_volume_kg=0,
            form_notes=["maintaining neutral spine well"],
            cues_given=["opposite arm-leg", "press low back into floor"],
        ))
        order += 1

        # Band pull-apart (sessions 3+)
        if i >= 2:
            bp_sets = [{"set": j, "reps": 15} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Band Pull-Apart",
                exercise_canonical="band_pull_apart",
                sets=bp_sets,
                total_volume_kg=0,
                form_notes=["good scapular retraction"],
            ))
            order += 1

        # Observation cards — one per session about energy/recovery
        obs_texts = [
            "First session. Low energy, 4 hours sleep (baby waking). Kept intensity low. Good attitude.",
            "Energy better today. Core activation improving. No diastasis symptoms during dead bugs.",
            "Progressed goblet squat to 10kg — handled it well. Confidence growing.",
            "Recovery going well. Mentioned sleeping better. Ready to add a third exercise next session.",
            "Best session yet. Moved to 12kg goblet squat. Core stable throughout. Great progress.",
        ]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.observation_card,
            sequence_order=order,
            observation_text=obs_texts[i],
        ))

    return sessions, entries, plans


def _seed_jake(
    db: AsyncSession, trainer: Trainer, client: Client,
) -> tuple[list[Session], list[SessionEntry], list[SessionPlan], list[InjuryFlag]]:
    """Jake Morrison — 10 sessions, beginner, fast gains. 2 plans, 1 injury flag."""
    sessions = []
    entries = []
    plans = []
    injuries = []

    # Two session plans
    plan1 = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Upper body focus. 4x8 bench press (start 40kg, add 2.5kg if last session was RPE <8). "
            "3x10 lat pulldown. 3x10 overhead press with dumbbells. "
            "Emphasize form over load — he's progressing fast and needs good habits."
        ),
        planned_for_date=_days_ago(60).date(),
    )
    plan2 = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Lower body day. 4x8 barbell back squat — watch depth and knee tracking. "
            "3x10 Romanian deadlift, focus on hinge pattern. "
            "3x12 lunges each side. Core work: 3x plank to failure. "
            "If back feels tight from last session, swap RDLs for leg press."
        ),
        planned_for_date=_days_ago(30).date(),
    )
    db.add(plan1)
    db.add(plan2)
    plans.extend([plan1, plan2])

    session_days = [70, 63, 56, 49, 42, 35, 28, 21, 14, 7]
    bench_weights = [40.0, 42.5, 45.0, 47.5, 50.0, 52.5, 55.0, 57.5, 60.0, 62.5]
    squat_weights = [40.0, 45.0, 50.0, 55.0, 60.0, 60.0, 65.0, 65.0, 70.0, 70.0]

    for i, days in enumerate(session_days):
        # Alternate upper/lower
        is_upper = i % 2 == 0

        session = Session(
            trainer_id=trainer.id,
            client_id=client.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=60),
            duration_minutes=60,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Jake session {i + 1} — {'upper' if is_upper else 'lower'} body",
            plan_id=None,  # linked after flush for plan-connected sessions
        )
        db.add(session)
        sessions.append(session)

        order = 1

        if is_upper:
            # Bench
            b_sets = [{"set": j, "weight_kg": bench_weights[i], "reps": 8, "rpe": 6 + i * 0.3} for j in range(1, 5)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Barbell Bench Press",
                exercise_canonical="barbell_bench_press",
                sets=b_sets,
                total_volume_kg=_compute_volume(b_sets),
                form_notes=["elbows flaring"] if i < 4 else ["better tuck, good progress"],
                cues_given=["tuck elbows", "leg drive"],
            ))
            order += 1

            # Lat pulldown
            lp_sets = [{"set": j, "weight_kg": 45 + i * 2.5, "reps": 10} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Lat Pulldown",
                exercise_canonical="lat_pulldown",
                sets=lp_sets,
                total_volume_kg=_compute_volume(lp_sets),
                form_notes=["pulling with arms initially"] if i < 3 else ["engaging lats better"],
                cues_given=["pull with elbows", "squeeze shoulder blades"],
            ))
            order += 1

            # OHP
            ohp_sets = [{"set": j, "weight_kg": 20 + i * 2, "reps": 10} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Overhead Press",
                exercise_canonical="overhead_press",
                sets=ohp_sets,
                total_volume_kg=_compute_volume(ohp_sets),
            ))
            order += 1
        else:
            # Squat
            s_sets = [{"set": j, "weight_kg": squat_weights[i], "reps": 8, "rpe": 6 + i * 0.3} for j in range(1, 5)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Barbell Back Squat",
                exercise_canonical="barbell_back_squat",
                sets=s_sets,
                total_volume_kg=_compute_volume(s_sets),
                form_notes=["depth improving"] if i > 3 else ["needs more depth"],
                cues_given=["chest up", "push knees out"],
            ))
            order += 1

            # RDL
            rdl_sets = [{"set": j, "weight_kg": 40 + i * 2.5, "reps": 10} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Romanian Deadlift",
                exercise_canonical="romanian_deadlift",
                sets=rdl_sets,
                total_volume_kg=_compute_volume(rdl_sets),
                form_notes=["hinge improving"],
                cues_given=["push hips back", "soft knees"],
            ))
            order += 1

            # Lunges
            lunge_sets = [{"set": j, "weight_kg": 10 + i, "reps": 12} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Lunges",
                exercise_canonical="lunges",
                sets=lunge_sets,
                total_volume_kg=_compute_volume(lunge_sets),
            ))
            order += 1

        # Observation card every 2-3 sessions
        if i in (2, 5, 8):
            obs_texts = {
                2: "Progressing well for a beginner. Form improving on bench. Needs cue reminders on squat depth.",
                5: "Hitting stride — weight jumps are consistent. Posture visibly better. Enjoys training.",
                8: "Mentioned lower back tightness after last squat session. Keeping an eye on it.",
            }
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.observation_card,
                sequence_order=order,
                observation_text=obs_texts[i],
            ))

    # Injury flag — lower back tightness, session 8
    injuries.append(InjuryFlag(
        client_id=client.id,
        session_id=None,  # linked after flush
        body_part="lower back",
        pain_level=3,
        description="Tightness after heavy squat session. No sharp pain, muscular. Responded well to stretching.",
        first_occurrence=_days_ago(21),
        last_occurrence=_days_ago(21),
        occurrence_count=1,
    ))

    return sessions, entries, plans, injuries


def _seed_elena(
    db: AsyncSession, trainer: Trainer, client: Client,
) -> tuple[list[Session], list[SessionEntry], list[SessionPlan], list[InjuryFlag]]:
    """Elena Vasquez — 15 sessions, elderly, long-term. 3 plans, 2 injury flags."""
    sessions = []
    entries = []
    plans = []
    injuries = []

    # Three session plans
    plan1 = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Baseline assessment and gentle introduction. Leg press (light), seated row, "
            "step-ups on low box. Focus on confidence and comfort in the gym. "
            "Watch hip ROM on step-ups given replacement history."
        ),
        planned_for_date=_days_ago(105).date(),
    )
    plan2 = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Progress leg press by 2.5kg if last session was comfortable. Add band pull-aparts "
            "for shoulder health. Continue seated row at same weight, focus on form. "
            "Monitor left shoulder — impingement was flaring last week."
        ),
        planned_for_date=_days_ago(70).date(),
    )
    plan3 = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text=(
            "Long-term progression check. She's been training 12+ weeks now. "
            "Test leg press at 55kg for 3x10. Introduce bird dogs for core/balance. "
            "Right hip has been bothering her — modify step-ups to lower box height. "
            "Goal: maintain independence and bone density."
        ),
        planned_for_date=_days_ago(28).date(),
    )
    db.add(plan1)
    db.add(plan2)
    db.add(plan3)
    plans.extend([plan1, plan2, plan3])

    session_days = [105, 98, 91, 84, 77, 70, 63, 56, 49, 42, 35, 28, 21, 14, 7]
    leg_press_weights = [
        30.0, 32.5, 35.0, 37.5, 40.0, 42.5, 42.5, 45.0, 45.0, 47.5,
        47.5, 50.0, 50.0, 52.5, 55.0,
    ]

    for i, days in enumerate(session_days):
        session = Session(
            trainer_id=trainer.id,
            client_id=client.id,
            started_at=_days_ago(days),
            ended_at=_days_ago(days) + timedelta(minutes=40),
            duration_minutes=40,
            processing_status=ProcessingStatusEnum.completed,
            raw_transcript=f"Elena session {i + 1} — steady progression",
            plan_id=None,  # linked after flush
        )
        db.add(session)
        sessions.append(session)

        order = 1

        # Leg press (every session)
        lp_sets = [{"set": j, "weight_kg": leg_press_weights[i], "reps": 10 if i < 10 else 12} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Leg Press",
            exercise_canonical="leg_press",
            sets=lp_sets,
            total_volume_kg=_compute_volume(lp_sets),
            form_notes=["full ROM", "no hip pain"] if i < 11 else ["monitoring right hip"],
            cues_given=["don't lock knees", "controlled descent"],
        ))
        order += 1

        # Seated row (every session)
        sr_sets = [{"set": j, "weight_kg": 20.0, "reps": 12} for j in range(1, 4)]
        entries.append(SessionEntry(
            session_id=None,
            client_id=client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=order,
            exercise_name="Seated Row",
            exercise_canonical="seated_row",
            sets=sr_sets,
            total_volume_kg=_compute_volume(sr_sets),
            form_notes=["good retraction"] if i > 3 else ["pulling with arms, cueing lats"],
            cues_given=["squeeze shoulder blades", "pull to belly button"],
        ))
        order += 1

        # Step-ups (alternating sessions)
        if i % 2 == 0:
            su_sets = [{"set": j, "weight_kg": 0, "reps": 8} for j in range(1, 4)]
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.exercise_card,
                sequence_order=order,
                exercise_name="Step-Ups",
                exercise_canonical="step_ups",
                sets=su_sets,
                total_volume_kg=0,
                form_notes=["balance improving"] if i > 5 else ["using rail for support"],
                cues_given=["drive through heel", "stand tall at top"],
            ))
            order += 1

        # Observation card roughly every 2 sessions
        if i % 2 == 0:
            obs_options = [
                "First session. Nervous but determined. Good baseline strength for her age. Hip ROM acceptable.",
                "Settling into routine. Likes the seated row. Energy good today.",
                "Left shoulder flaring — avoided overhead movements. Using ice after sessions.",
                "Shoulder feeling better. Added band pull-aparts as prehab. Good session.",
                "Steady progress. Balance on step-ups much improved. Confident in the gym now.",
                "Mentioned right hip stiffness after gardening. Reducing step-up box height.",
                "Hip still bothering her but manageable. Leg press feels strong at 50kg.",
                "Great session. 15 weeks in — visible improvements in posture and confidence.",
            ]
            obs_idx = min(i // 2, len(obs_options) - 1)
            entries.append(SessionEntry(
                session_id=None,
                client_id=client.id,
                entry_type=EntryTypeEnum.observation_card,
                sequence_order=order,
                observation_text=obs_options[obs_idx],
            ))

    # Injury flag 1: left shoulder impingement (sessions 3-5, resolved)
    injuries.append(InjuryFlag(
        client_id=client.id,
        session_id=None,  # linked to session 3 after flush
        body_part="left shoulder",
        pain_level=4,
        description="Impingement flare during lateral raises. Avoided all overhead work. Ice after sessions.",
        first_occurrence=_days_ago(91),
        last_occurrence=_days_ago(77),
        occurrence_count=3,
        resolved=True,
        resolved_at=_days_ago(70),
    ))

    # Injury flag 2: right hip discomfort (session 12+, active)
    injuries.append(InjuryFlag(
        client_id=client.id,
        session_id=None,  # linked to session 12 after flush
        body_part="right hip",
        pain_level=3,
        description="Discomfort during step-ups and after prolonged sitting. History of hip replacement. Managing with lower box height.",
        first_occurrence=_days_ago(28),
        last_occurrence=_days_ago(7),
        occurrence_count=4,
    ))

    return sessions, entries, plans, injuries


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

async def seed(db: AsyncSession, *, commit: bool = True) -> None:
    """Seed the database with realistic demo data. Truncates first for idempotency.

    Args:
        db: Async database session.
        commit: If True (default), commits at the end. Set to False in tests
                where the test harness manages transactions.
    """
    # Truncate in FK-safe order
    await db.execute(text(
        "TRUNCATE TABLE brain_messages, brain_conversations, injury_flags, "
        "session_entries, sessions, session_plans, client_analysis, "
        "clients, trainers, exercises CASCADE"
    ))

    # --- Exercises ---
    exercises = _seed_exercises(db)
    await db.flush()

    # --- Trainer ---
    trainer = Trainer(
        email="coach@supertrainer.app",
        name="Coach Pranav",
        phone="+1-555-0100",
    )
    db.add(trainer)
    await db.flush()

    # --- Clients ---
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
        c = Client(trainer_id=trainer.id, **data)
        db.add(c)
        clients.append(c)
    await db.flush()

    sarah, marcus, aisha, jake, elena = clients

    # --- Seed each client ---

    # Sarah (1 session)
    sarah_sessions, sarah_entries = _seed_sarah(db, trainer, sarah)
    await db.flush()
    for entry in sarah_entries:
        entry.session_id = sarah_sessions[0].id
        db.add(entry)
    await db.flush()

    # Marcus (3 sessions)
    marcus_sessions, marcus_entries, marcus_injuries = _seed_marcus(db, trainer, marcus)
    await db.flush()
    # Link entries to sessions: 4 exercise + optional obs per session
    entry_idx = 0
    for si, sess in enumerate(marcus_sessions):
        # 4 exercise cards per session
        for _ in range(4):
            marcus_entries[entry_idx].session_id = sess.id
            db.add(marcus_entries[entry_idx])
            entry_idx += 1
        # Session 2 (index 1) has an observation card
        if si == 1:
            marcus_entries[entry_idx].session_id = sess.id
            db.add(marcus_entries[entry_idx])
            entry_idx += 1
    await db.flush()
    # Link injury to session 3
    marcus_injuries[0].session_id = marcus_sessions[2].id
    db.add(marcus_injuries[0])
    await db.flush()

    # Aisha (5 sessions, 1 plan)
    aisha_sessions, aisha_entries, aisha_plans = _seed_aisha(db, trainer, aisha)
    await db.flush()
    # Link plan to sessions 3, 4, 5 (the ones after plan was created)
    for sess in aisha_sessions[2:]:
        sess.plan_id = aisha_plans[0].id
    # Link entries to sessions
    entry_idx = 0
    for si, sess in enumerate(aisha_sessions):
        # 2 exercise cards per session (3 for sessions 3+)
        num_exercises = 3 if si >= 2 else 2
        for _ in range(num_exercises):
            aisha_entries[entry_idx].session_id = sess.id
            db.add(aisha_entries[entry_idx])
            entry_idx += 1
        # 1 observation per session
        aisha_entries[entry_idx].session_id = sess.id
        db.add(aisha_entries[entry_idx])
        entry_idx += 1
    await db.flush()

    # Jake (10 sessions, 2 plans, 1 injury)
    jake_sessions, jake_entries, jake_plans, jake_injuries = _seed_jake(db, trainer, jake)
    await db.flush()
    # Link plan1 to sessions 1-5 (first 5), plan2 to sessions 6-10
    for sess in jake_sessions[:5]:
        sess.plan_id = jake_plans[0].id
    for sess in jake_sessions[5:]:
        sess.plan_id = jake_plans[1].id
    # Link entries to sessions
    entry_idx = 0
    for si, sess in enumerate(jake_sessions):
        # 3 exercise cards per session (upper or lower)
        for _ in range(3):
            jake_entries[entry_idx].session_id = sess.id
            db.add(jake_entries[entry_idx])
            entry_idx += 1
        # Observation on sessions 3, 6, 9 (indices 2, 5, 8)
        if si in (2, 5, 8):
            jake_entries[entry_idx].session_id = sess.id
            db.add(jake_entries[entry_idx])
            entry_idx += 1
    await db.flush()
    # Link injury to session 8 (index 7)
    jake_injuries[0].session_id = jake_sessions[7].id
    db.add(jake_injuries[0])
    await db.flush()

    # Elena (15 sessions, 3 plans, 2 injuries)
    elena_sessions, elena_entries, elena_plans, elena_injuries = _seed_elena(db, trainer, elena)
    await db.flush()
    # Link plans to sessions
    for sess in elena_sessions[:5]:
        sess.plan_id = elena_plans[0].id
    for sess in elena_sessions[5:10]:
        sess.plan_id = elena_plans[1].id
    for sess in elena_sessions[10:]:
        sess.plan_id = elena_plans[2].id
    # Link entries to sessions
    entry_idx = 0
    for si, sess in enumerate(elena_sessions):
        # 2 exercises always (leg press + seated row)
        for _ in range(2):
            elena_entries[entry_idx].session_id = sess.id
            db.add(elena_entries[entry_idx])
            entry_idx += 1
        # Step-ups on even sessions
        if si % 2 == 0:
            elena_entries[entry_idx].session_id = sess.id
            db.add(elena_entries[entry_idx])
            entry_idx += 1
        # Observation on even sessions
        if si % 2 == 0:
            elena_entries[entry_idx].session_id = sess.id
            db.add(elena_entries[entry_idx])
            entry_idx += 1
    await db.flush()
    # Link injuries
    elena_injuries[0].session_id = elena_sessions[2].id  # shoulder, session 3
    elena_injuries[1].session_id = elena_sessions[11].id  # hip, session 12
    for inj in elena_injuries:
        db.add(inj)
    await db.flush()

    if commit:
        await db.commit()

    # Summary
    total_sessions = len(sarah_sessions) + len(marcus_sessions) + len(aisha_sessions) + len(jake_sessions) + len(elena_sessions)
    total_entries = len(sarah_entries) + len(marcus_entries) + len(aisha_entries) + len(jake_entries) + len(elena_entries)
    total_plans = len(aisha_plans) + len(jake_plans) + len(elena_plans)
    total_injuries = len(marcus_injuries) + len(jake_injuries) + len(elena_injuries)
    print(
        f"Seeded: 1 trainer, 5 clients, {total_sessions} sessions, "
        f"{total_entries} entries, {total_plans} plans, {total_injuries} injury flags, "
        f"{len(exercises)} exercises"
    )


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
