"""The Brain — answers a trainer's questions about their clients.

First version: the whole roster (profiles, every session and entry) goes into
one Claude call as context. That fits comfortably for a trainer's real data
size today; retrieval (pgvector) replaces it once histories outgrow a prompt.
"""

from datetime import datetime, timezone

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Client, Session, SessionEntry
from app.services.parser import DEFAULT_MODEL
from app.services.session_summary import describe_entry

BRAIN_SYSTEM_PROMPT = """You are the Brain inside SuperTrainer, an app personal trainers use to log sessions.
The trainer asks about their clients. Answer from the training data below, which is everything the app knows.

Rules:
- Answer only from the data. If it doesn't say, say so in one sentence.
- Never state a cause, plan, trend or advice the data doesn't state ("was avoided because it flared", \
not "it flared because of it"). Repeated identical notes mean "steady", not "improving".
- Be brief: at most 120 words. Lead with the answer, then the numbers that support it.
- Say when things happened relative to today ("3 days ago", "last week"), never as calendar dates.
- Use the trainer's terms ("Bench press 3x5 at 80kg").
- Plain text: no markdown, asterisks or headings. Short "- " lines are fine for a list.
- If the data shows pain or an injury that matters for the question, mention it.
- Each detail belongs to the session it is listed under; don't move a note from one session to another.
- For how things are now or today, use the most recent sessions. An older note is history, not current.
- For a question about several clients, check every client's injury history, notes and sessions."""


def _days_ago(when: datetime, now: datetime) -> str:
    days = (now.date() - when.date()).days
    return "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"


async def build_brain_context(db: AsyncSession, trainer_id, now: datetime) -> str:
    clients = list(
        (await db.execute(
            select(Client).where(Client.trainer_id == trainer_id, Client.archived.is_(False)).order_by(Client.name)
        )).scalars()
    )
    sessions = list(
        (await db.execute(
            select(Session).where(Session.trainer_id == trainer_id).order_by(Session.started_at)
        )).scalars()
    )
    entries = list(
        (await db.execute(
            select(SessionEntry)
            .join(Session, Session.id == SessionEntry.session_id)
            .where(Session.trainer_id == trainer_id)
            .order_by(SessionEntry.sequence_order)
        )).scalars()
    )
    entries_by_session: dict = {}
    for entry in entries:
        entries_by_session.setdefault(entry.session_id, []).append(entry)

    # Every client's profile up front, so a roster-wide question can't miss one
    roster = ["## Roster"] + [
        f"- {c.name}: goals {', '.join(c.goals or []) or 'not recorded'}; "
        f"injury history: {c.injury_history or 'none recorded'}"
        for c in clients
    ]
    blocks = ["\n".join(roster)]
    for client in clients:
        lines = [
            f"## {client.name}",
            f"Goals: {', '.join(client.goals or []) or 'not recorded'}",
            f"Injury history: {client.injury_history or 'none recorded'}",
        ]
        for session in (s for s in sessions if s.client_id == client.id):
            length = f", {session.duration_minutes} min" if session.duration_minutes else ""
            status = "" if session.ended_at else " (in progress)"
            lines.append(f"Session {_days_ago(session.started_at, now)}{length}{status}:")
            for entry in entries_by_session.get(session.id, []):
                lines.append(f"  - {describe_entry(entry)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


async def ask_brain(db: AsyncSession, trainer_id, question: str) -> str:
    now = datetime.now(timezone.utc)
    context = await build_brain_context(db, trainer_id, now)
    response = await anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key).messages.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        temperature=0,
        system=f"{BRAIN_SYSTEM_PROMPT}\n\n# Training data\n\n{context}",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
