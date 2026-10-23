"""Session summaries — Claude's 2-3 sentence recap of a finished session.

When a trainer browses history, the recap should bring the whole session
back without expanding it: what was done, how it went, and anything that
stood out (new pain, a form breakdown, a personal best).
"""

import itertools

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Client, EntryTypeEnum, Session, SessionEntry
from app.services.parser import DEFAULT_MODEL

SUMMARY_SYSTEM_PROMPT = """You write the session recap a personal trainer reads later to remember a session.

Write 2-3 sentences, no more than 60 words:
1. What was done: the main exercises and the load, in the trainer's terms.
2. How it went: effort (RPE) and anything the data says went well or badly.
3. Anything worth remembering next time: pain, a form breakdown, a cue that was given, \
or a personal best.

Rules:
- Only state what the session data says. Never invent numbers, feelings, causes or advice.
- "Next time" points come only from the data: a cue that was given, pain, a form note or a note.
- Cues have no timing: one may have been said after the problem, for next time. Never say something \
happened "despite" a cue or after a cue; say only that the cue was given.
- Don't judge effort ("solid", "worked hard", "found it tough") unless an RPE or a note says so. \
An RPE belongs to the set it is logged on.
- Notes are listed in time order, so a note is not necessarily about the exercise just above it. \
Tie a note to an exercise only when the note, a cue or a form note names it; otherwise mention it without one.
- Call a weight a personal best only when its line shows [previous best: N] and the new weight is above N.
- Write like a trainer's note: "Goblet squats 3x10 at 16kg", not "The client performed".
- Refer to the client by first name.
- Plain text: no markdown, asterisks, headings, lists, emoji or quotation marks."""


def describe_entry(entry: SessionEntry) -> str:
    """One entry as a line of plain text, for the summary and the Brain."""
    if entry.entry_type != EntryTypeEnum.exercise_card:
        about_set = f" (logged against set {entry.attached_to_set})" if entry.attached_to_set else ""
        return f"Note: {entry.observation_text}{about_set}"
    name = entry.exercise_canonical or entry.exercise_name or "Unknown exercise"
    line = f"{name}: {format_sets(entry)}"
    if entry.form_notes:
        line += f". Form notes: {'; '.join(entry.form_notes)}"
    if entry.cues_given:
        # The data doesn't say when a cue was said; it may have been "for next time"
        line += f". Cues (timing not recorded): {'; '.join(entry.cues_given)}"
    return line


def set_weight(s: dict) -> tuple[float, str] | None:
    """A set's weight and unit. Voice-logged sets store `weight` + `weight_unit`;
    older and seeded sets store `weight_kg` (the same pair entry_service reads)."""
    if s.get("weight") is not None:
        return s["weight"], s.get("weight_unit", "kg")
    if s.get("weight_kg") is not None:
        return s["weight_kg"], "kg"
    return None


def format_sets(entry: SessionEntry) -> str:
    """Sets as text, with identical sets in a row grouped ("3 sets of 12 reps at 20kg")
    so the reader never has to count them."""
    parts = []
    for s in entry.sets or []:
        if s.get("duration_seconds"):
            text = f"{s['duration_seconds']}s"
        else:
            text = f"{s.get('reps', '?')} reps"
        if weight := set_weight(s):
            text += f" at {weight[0]:g}{weight[1]}"
        if s.get("rpe") is not None:
            text += f", RPE {s['rpe']}"
        if s.get("notes"):
            text += f" ({s['notes']})"
        parts.append(text)
    grouped = [(text, len(list(run))) for text, run in itertools.groupby(parts)]
    return "; ".join(
        f"{count} sets of {text}" if count > 1 else f"1 set of {text}" for text, count in grouped
    ) or "no sets recorded"


async def _previous_bests(db: AsyncSession, session: Session) -> dict[str, float]:
    """Heaviest weight per exercise in this client's earlier sessions."""
    rows = await db.execute(
        select(SessionEntry.exercise_canonical, SessionEntry.sets)
        .join(Session, Session.id == SessionEntry.session_id)
        .where(
            Session.client_id == session.client_id,
            Session.started_at < session.started_at,
            SessionEntry.entry_type == EntryTypeEnum.exercise_card,
        )
    )
    bests: dict[str, float] = {}
    for canonical, sets in rows:
        for s in sets or []:
            weight = set_weight(s)
            if canonical and weight:
                bests[canonical] = max(bests.get(canonical, 0), weight[0])
    return bests


def build_summary_prompt(
    client: Client,
    session: Session,
    entries: list[SessionEntry],
    previous_bests: dict[str, float],
) -> str:
    lines = [
        f"Client: {client.name}",
        f"Goals: {', '.join(client.goals or []) or 'not recorded'}",
        f"Injury history: {client.injury_history or 'none recorded'}",
    ]
    if session.duration_minutes:
        lines.append(f"Session length: {session.duration_minutes} minutes")
    lines += ["", "Session, in order:"]
    for entry in entries:
        line = f"- {describe_entry(entry)}"
        if entry.entry_type == EntryTypeEnum.exercise_card and entry.exercise_canonical in previous_bests:
            line += f" [previous best: {previous_bests[entry.exercise_canonical]}]"
        lines.append(line)
    return "\n".join(lines)


async def summarize_session(db: AsyncSession, session: Session) -> str | None:
    """Write the recap, or return None for a session with nothing recorded."""
    entries = list(
        (
            await db.execute(
                select(SessionEntry)
                .where(SessionEntry.session_id == session.id)
                .order_by(SessionEntry.sequence_order)
            )
        ).scalars()
    )
    if not entries:
        return None

    client = await db.get(Client, session.client_id)
    prompt = build_summary_prompt(client, session, entries, await _previous_bests(db, session))

    response = await anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key).messages.create(
        model=DEFAULT_MODEL,
        max_tokens=300,
        temperature=0,
        system=SUMMARY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None
