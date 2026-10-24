"""Pre-session briefs — Claude's notes on a client before today's session.

A trainer opens the day's schedule and taps a session to see what matters
about that client: how their lifts are moving, any pain from the past few
weeks, and what they haven't trained lately. The facts (weight changes,
untrained muscle groups, pain notes) are worked out here in code, so Claude
only words them; it never does the arithmetic or decides what counts as a gap.
"""

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Client, EntryTypeEnum, Session, SessionEntry
from app.services.brain import _days_ago
from app.services.parser import DEFAULT_MODEL
from app.services.session_summary import describe_entry, set_weight
from app.services.transcription import load_exercise_db
from app.services.validation import extract_pain_mentions, get_exercise_lookup

WINDOW_DAYS = 28

# Muscle group for each primary-muscle keyword in the exercise database.
# Order matters: "biceps femoris" is a hamstring, so it's checked before "biceps".
MUSCLE_GROUPS: list[tuple[str, str]] = [
    ("biceps femoris", "hamstrings"),
    ("semimembranosus", "hamstrings"),
    ("semitendinosus", "hamstrings"),
    ("hamstring", "hamstrings"),
    ("rectus femoris", "quads"),
    ("vastus", "quads"),
    ("quadriceps", "quads"),
    ("gluteus", "glutes"),
    ("gastrocnemius", "calves"),
    ("soleus", "calves"),
    ("pectoralis", "chest"),
    ("deltoid", "shoulders"),
    ("latissimus", "back"),
    ("rhomboid", "back"),
    ("trapezius", "back"),
    ("teres", "back"),
    ("biceps brachii", "biceps"),
    ("brachialis", "biceps"),
    ("triceps", "triceps"),
    ("abdominis", "core"),
    ("oblique", "core"),
    ("erector spinae", "core"),
    ("multifidus", "core"),
    ("quadratus lumborum", "core"),
]
ALL_GROUPS = list(dict.fromkeys(group for _, group in MUSCLE_GROUPS))

BRIEF_SYSTEM_PROMPT = """You write the notes a personal trainer reads just before a session with a client.

Write 2-4 notes, one per line, each starting with "- ". At most 80 words in total.
Pick what matters most for today's session, in this order:
1. Pain or an injury flag from recent sessions, and whether it has come up more than once.
2. A lift whose weight has dropped, or a big jump, from the "Weight changes" list.
3. A muscle group from the "Not trained" list that fits the client's goals.
4. What the last session covered, if there's room.

Rules:
- Use only the facts below. Never invent numbers, causes, diagnoses or feelings.
- Weight changes and untrained muscle groups are already worked out: quote them as given, never recalculate. \
If the untrained groups are unknown, don't mention gaps.
- Keep each fact with the exercise and set it was logged on, and give a set's reason in its own words \
(a set "stopped, wrist hurt" was stopped for the wrist, not for fatigue). A note from one exercise is not about the whole session.
- A note may end with one short suggestion that follows directly from its fact \
("could be worth checking before pressing", "a set of calf raises would cover it"). \
Never suggest anything medical beyond checking in with the client.
- Say when things happened relative to today ("last week", "12 days ago"), never as calendar dates.
- Refer to the client by first name. Use the trainer's terms ("Lat pulldown 3x10 at 40kg").
- Plain text: no markdown, asterisks, headings or emoji."""


def muscle_group(muscle: str) -> str | None:
    muscle = muscle.lower()
    return next((group for keyword, group in MUSCLE_GROUPS if keyword in muscle), None)


@lru_cache
def _groups_by_canonical() -> dict[str, frozenset[str]]:
    return {
        ex["canonical_name"]: frozenset(g for m in ex.get("primary_muscles", []) if (g := muscle_group(m)))
        for ex in load_exercise_db()
    }


def resolve_exercise(entry: SessionEntry) -> str | None:
    """The exercise database's name for an entry, or None if it isn't a known name or alias.
    Seeded entries store "goblet_squat" or "deadlift". No fuzzy matching: a near miss
    would credit the wrong muscles, and a missed one only makes the gaps unknown."""
    raw = entry.exercise_canonical or entry.exercise_name
    return get_exercise_lookup().get(raw.replace("_", " ").strip().lower()) if raw else None


def _exercises(sessions: list[Session], entries: dict):
    """(session, entry, database name or None) for every exercise card, oldest first."""
    for session in sessions:
        for entry in entries.get(session.id, []):
            if entry.entry_type == EntryTypeEnum.exercise_card:
                yield session, entry, resolve_exercise(entry)


def _top_weight_kg(entry: SessionEntry) -> float | None:
    """The heaviest set's weight. Validation stores every weight in kg."""
    weights = [pair[0] for s in entry.sets or [] if (pair := set_weight(s)) and pair[0] > 0]
    return max(weights) if weights else None


def weight_changes(sessions: list[Session], entries: dict, now: datetime) -> list[str]:
    """For each lift done at least twice with weight, its heaviest set first vs last."""
    history: dict[str, list[tuple[datetime, float]]] = {}
    for session, entry, name in _exercises(sessions, entries):
        if (top := _top_weight_kg(entry)) is not None:
            history.setdefault(name or entry.exercise_name, []).append((session.started_at, top))
    lines = []
    for name, points in history.items():
        if len(points) < 2:
            continue
        (first_at, first), (last_at, last) = points[0], points[-1]
        change = round((last - first) / first * 100)
        trend = "no change" if change == 0 else f"{'+' if change > 0 else ''}{change}%"
        lines.append(
            f"{name}: heaviest set {first:g}kg {_days_ago(first_at, now)}, "
            f"{last:g}kg {_days_ago(last_at, now)} ({trend}, {len(points)} sessions)"
        )
    return lines


def untrained_groups(sessions: list[Session], entries: dict) -> tuple[list[str], list[str]]:
    """Major muscle groups no exercise trained, and exercises whose muscles are unknown.
    While any exercise is unknown, the gaps can't be trusted."""
    trained: set[str] = set()
    unknown: list[str] = []
    for _, entry, name in _exercises(sessions, entries):
        if name is None:
            unknown.append(entry.exercise_name or entry.exercise_canonical or "unnamed exercise")
        else:
            trained |= _groups_by_canonical().get(name, frozenset())
    return [g for g in ALL_GROUPS if g not in trained], list(dict.fromkeys(unknown))


def pain_notes(sessions: list[Session], entries: dict, now: datetime) -> list[str]:
    """Every note or set note that mentions pain, or an observation flagged red or yellow."""
    lines = []
    for session in sessions:
        when = _days_ago(session.started_at, now)
        for entry in entries.get(session.id, []):
            if entry.entry_type == EntryTypeEnum.exercise_card:
                name = resolve_exercise(entry) or entry.exercise_name
                for s in entry.sets or []:
                    if s.get("notes") and extract_pain_mentions(s["notes"]):
                        lines.append(f"{when}, during {name}: {s['notes']}")
            elif entry.observation_text and (
                entry.flag_color in ("red", "yellow") or extract_pain_mentions(entry.observation_text)
            ):
                lines.append(f"{when}: {entry.observation_text}")
    return lines


async def build_brief_prompt(db: AsyncSession, client: Client, before: datetime, now: datetime) -> str | None:
    """The facts for a client's brief, from finished sessions in the last four weeks before `before`.
    None when there is nothing to brief on."""
    sessions = list(
        (await db.execute(
            select(Session)
            .where(
                Session.client_id == client.id,
                Session.ended_at.is_not(None),
                Session.started_at < before,
                Session.started_at >= before - timedelta(days=WINDOW_DAYS),
            )
            .order_by(Session.started_at)
        )).scalars()
    )
    if not sessions:
        return None
    rows = (await db.execute(
        select(SessionEntry)
        .where(SessionEntry.session_id.in_([s.id for s in sessions]))
        .order_by(SessionEntry.sequence_order)
    )).scalars()
    entries: dict = {}
    for entry in rows:
        entries.setdefault(entry.session_id, []).append(entry)

    changes = weight_changes(sessions, entries, now)
    gaps, unknown = untrained_groups(sessions, entries)
    pain = pain_notes(sessions, entries, now)
    if unknown:
        gap_line = "Not trained in the last four weeks: unknown (unrecognised exercises: " + ", ".join(unknown) + ")"
    else:
        gap_line = "Not trained in the last four weeks: " + (", ".join(gaps) or "every major muscle group was trained")
    last = sessions[-1]
    lines = [
        f"Client: {client.name}",
        f"Goals: {', '.join(client.goals or []) or 'not recorded'}",
        f"Injury history: {client.injury_history or 'none recorded'}",
        f"Sessions in the last four weeks: {len(sessions)}",
        "",
        f"Last session ({_days_ago(last.started_at, now)}):",
        *[f"- {describe_entry(e)}" for e in entries.get(last.id, [])],
        "",
        "Weight changes over the last four weeks:",
        *([f"- {c}" for c in changes] or ["- none: no lift was done twice with weight"]),
        "",
        "Pain and flags in the last four weeks:",
        *([f"- {p}" for p in pain] or ["- none logged"]),
        "",
        gap_line,
    ]
    return "\n".join(lines)


async def write_brief(db: AsyncSession, session: Session) -> str | None:
    """Claude's notes for the client of an upcoming or in-progress session."""
    client = await db.get(Client, session.client_id)
    now = datetime.now(timezone.utc)
    prompt = await build_brief_prompt(db, client, before=max(session.started_at, now), now=now)
    if prompt is None:
        return None
    response = await anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key).messages.create(
        model=DEFAULT_MODEL,
        max_tokens=300,
        temperature=0,
        system=BRIEF_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
