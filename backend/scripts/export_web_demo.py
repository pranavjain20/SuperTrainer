"""Record real backend output for the web demo (mobile/src/demo).

The web demo has no server. It replays what this script records from a real
local backend, so visitors see genuine pipeline output:
- the seeded clients and sessions, each finished session with its AI summary
- the Deepgram + Claude result for each sample voice clip, in order
- the AI summary each client would get after 1, 2, ... 6 of those clips
- the Brain's answers to the suggested questions
- each client's pre-session brief (the AI notes on today's upcoming sessions)
- a plan dictation, transcribed and parsed

Run against a freshly seeded local backend (macOS: clips are spoken with `say`):
    python -m app.seed
    uvicorn app.main:app --port 8000
    python scripts/export_web_demo.py [--voice-dir DIR]

--briefs-only re-records just the briefs into the existing fixture.
--voice-dir uses real recordings instead of `say`: DIR/clip-1.m4a ... clip-6.m4a
and DIR/plan.m4a, saying the lines in SESSION_CLIPS and PLAN_CLIP.

Writes mobile/src/demo/fixture.json and mobile/public/demo/*.m4a.
Moves the seeded sessions' dates in the local database (see anchor_to_today).
Makes about 80 Claude calls and 7 Deepgram calls (well under a dollar).
"""

import argparse
import asyncio
import itertools
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings  # noqa: E402
from app.services.transcription import load_exercise_db  # noqa: E402
from app.services.workout_classifier import classify_workout, exercise_region  # noqa: E402

MOBILE = Path(__file__).resolve().parents[2] / "mobile"
FIXTURE_PATH = MOBILE / "src" / "demo" / "fixture.json"
AUDIO_DIR = MOBILE / "public" / "demo"  # the web export serves public/ at the site root
BRAIN_QUESTIONS = json.loads((MOBILE / "src" / "constants" / "brainSuggestions.json").read_text())
VOICE = "Samantha"

# One session's worth of clips, in the order a trainer would say them: a note
# right after the set it's about. Clip 4 corrects clip 3, which exercises the
# parser's modify path.
SESSION_CLIPS = [
    "Goblet squats, three sets of ten at sixteen kilos. The last set was an RPE of eight.",
    "Knees caved in a little on the last few squat reps. Cue knees out next time.",
    "Romanian deadlifts, three sets of eight at twenty five kilos. "
    "Hamstrings felt tight on the last set.",
    "Actually, that last set of deadlifts was thirty kilos, not twenty five.",
    "Push ups, three sets of twelve, bodyweight.",
    "Plank, three rounds of forty five seconds.",
]
PLAN_CLIP = (
    "Next session is legs. Back squats four sets of eight at sixty kilos, "
    "walking lunges three sets of ten each side, and leg press three sets of twelve at one hundred kilos."
)

# Entry fields the API sets itself; everything else is copied when rebuilding a session
SERVER_FIELDS = {"id", "session_id", "client_id", "sequence_order", "created_at"}


def get_all(api: httpx.Client, path: str) -> list[dict]:
    """Follow cursor pagination to the end."""
    items: list[dict] = []
    cursor = None
    while True:
        params = {"limit": 100, **({"cursor": cursor} if cursor else {})}
        body = api.get(path, params=params).raise_for_status().json()
        items += body["data"]
        if not body["meta"].get("has_more"):
            return items
        cursor = body["meta"]["cursor"]


def make_clip(text_: str, name: str, voice_dir: Path | None) -> Path:
    """mobile/public/demo/<name>.m4a: the real recording if given, else `say`."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIO_DIR / f"{name}.m4a"
    if voice_dir:
        shutil.copyfile(voice_dir / f"{name}.m4a", out)
        return out
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "clip.aiff"
        subprocess.run(["say", "-v", VOICE, "-r", "175", "-o", str(aiff), text_], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(out)], check=True)
    return out


def post_audio(api: httpx.Client, path: str, audio: Path) -> dict:
    files = {"audio": (audio.name, audio.read_bytes(), "audio/mp4")}
    return api.post(path, files=files, timeout=60).raise_for_status().json()["data"]


def timed_post(api: httpx.Client, path: str, **kwargs) -> tuple[dict, int]:
    """POST and return (data, milliseconds it took), so the demo can wait as long."""
    start = time.monotonic()
    data = api.post(path, timeout=90, **kwargs).raise_for_status().json()["data"]
    return data, round((time.monotonic() - start) * 1000)


async def anchor_to_today() -> int:
    """Move every seeded date by whole days so the latest session falls on today.

    The seed's newest session is a few days old, but the demo opens on today.
    Shifting the database first means the Brain's "3 days ago" and the demo's
    dates agree.
    """
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        latest = (await conn.execute(text("SELECT max(started_at)::date FROM sessions"))).scalar_one()
        days = (datetime.now(timezone.utc).date() - latest).days
        shift = f"interval '{days} days'"
        await conn.execute(text(
            f"UPDATE sessions SET started_at = started_at + {shift}, ended_at = ended_at + {shift}, "
            f"scheduled_for = scheduled_for + {shift}"
        ))
        await conn.execute(text(
            f"UPDATE session_entries SET performed_at = performed_at + {shift}, created_at = created_at + {shift}"
        ))
        await conn.execute(text(f"UPDATE session_plans SET planned_for_date = planned_for_date + {days}"))
    await engine.dispose()
    return days


def classifier_cases() -> tuple[dict[str, str], list[dict]]:
    """Each exercise's region, plus expected labels the demo's classifier must match."""
    exercises = load_exercise_db()
    regions = {
        ex["canonical_name"]: region
        for ex in exercises
        if (region := exercise_region(ex)) is not None
    }
    # One representative exercise per region, combined every way up to 4 long,
    # covers every branch: dominant region, push+pull, full body, empty.
    reps: dict[str, str] = {}
    for name, region in regions.items():
        reps.setdefault(region, name)
    pool = sorted(reps.values()) + ["Not An Exercise"]
    cases = [
        {"names": list(combo), "expected": classify_workout(list(combo))}
        for n in range(0, 5)
        for combo in itertools.combinations_with_replacement(pool, n)
    ]
    return regions, cases


def record_clip_summaries(api: httpx.Client, clients: list[dict], entries_after: list[list[dict]]) -> dict:
    """For each client, the summary of a session holding the first k clips' entries."""
    summaries: dict[str, list[dict]] = {}
    for client in clients:
        summaries[client["id"]] = []
        for k, entries in enumerate(entries_after, start=1):
            now = datetime.now(timezone.utc).isoformat()
            session = api.post(
                "/api/v1/sessions", json={"client_id": client["id"], "started_at": now},
            ).raise_for_status().json()["data"]
            try:
                for entry in entries:
                    body = {key: value for key, value in entry.items() if key not in SERVER_FIELDS}
                    api.post(f"/api/v1/sessions/{session['id']}/entries", json=body).raise_for_status()
                api.patch(
                    f"/api/v1/sessions/{session['id']}", json={"ended_at": datetime.now(timezone.utc).isoformat()},
                ).raise_for_status()
                data, ms = timed_post(api, f"/api/v1/sessions/{session['id']}/summary")
            finally:
                api.delete(f"/api/v1/sessions/{session['id']}")
            summaries[client["id"]].append({"ai_summary": data["ai_summary"], "ms": ms})
            print(f"summary {client['name']} after {k} clip(s): {data['ai_summary']!r}")
    return summaries


def record_briefs(api: httpx.Client, clients: list[dict]) -> dict:
    """Each client's brief, as the app would show it on a session later today."""
    briefs = {}
    for client in clients:
        later = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        session = api.post(
            "/api/v1/sessions", json={"client_id": client["id"], "started_at": later, "scheduled_for": later},
        ).raise_for_status().json()["data"]
        try:
            data, ms = timed_post(api, f"/api/v1/sessions/{session['id']}/brief")
        finally:
            api.delete(f"/api/v1/sessions/{session['id']}")
        briefs[client["id"]] = {"ai_brief": data["ai_brief"], "ms": ms}
        print(f"brief {client['name']}: {data['ai_brief']!r}")
    return briefs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--voice-dir", type=Path, help="real recordings to use instead of `say`")
    parser.add_argument("--briefs-only", action="store_true", help="re-record only the briefs")
    args = parser.parse_args()
    api = httpx.Client(base_url=args.api)

    if args.briefs_only:
        print(f"moved seeded dates by {asyncio.run(anchor_to_today())} days")
        fixture = json.loads(FIXTURE_PATH.read_text())
        fixture["session_briefs"] = record_briefs(api, get_all(api, "/api/v1/clients"))
        FIXTURE_PATH.write_text(json.dumps(fixture, indent=1) + "\n")
        print(f"wrote briefs to {FIXTURE_PATH}")
        return

    # 1. Dates on today, then a summary for every finished seeded session.
    print(f"moved seeded dates by {asyncio.run(anchor_to_today())} days")
    clients = get_all(api, "/api/v1/clients")
    for client in clients:
        for s in get_all(api, f"/api/v1/clients/{client['id']}/sessions"):
            if s["ended_at"]:
                api.post(f"/api/v1/sessions/{s['id']}/summary", timeout=90).raise_for_status()

    # 2. The Brain's answers, from the seeded data.
    brain = []
    for question in BRAIN_QUESTIONS:
        data, ms = timed_post(api, "/api/v1/brain/ask", json={"question": question})
        brain.append({"question": question, "answer": data["answer"], "ms": ms})
        print(f"brain: {question!r} -> {data['answer'][:80]!r}...")

    # 2b. Each client's brief for a session later today.
    briefs = record_briefs(api, clients)

    # 3. Snapshot the seeded data before the script adds anything.
    sessions, entries, plans = [], [], []
    for client in clients:
        client_sessions = get_all(api, f"/api/v1/clients/{client['id']}/sessions")
        sessions += client_sessions
        plans += get_all(api, f"/api/v1/clients/{client['id']}/plans")
        for s in client_sessions:
            entries += api.get(f"/api/v1/sessions/{s['id']}/entries").raise_for_status().json()["data"]

    # 4. Each session clip through the real pipeline, in order, in one scratch session.
    scratch = api.post(
        "/api/v1/sessions",
        json={"client_id": clients[0]["id"], "started_at": datetime.now(timezone.utc).isoformat()},
    ).raise_for_status().json()["data"]
    clips, entries_after = [], []
    try:
        for i, line in enumerate(SESSION_CLIPS, start=1):
            audio = make_clip(line, f"clip-{i}", args.voice_dir)
            result = post_audio(api, f"/api/v1/sessions/{scratch['id']}/voice-clip", audio)
            print(f"clip {i}: {result['transcript']!r} -> "
                  f"{len(result['entries_created'])} created, {len(result['entries_modified'])} modified")
            clips.append({"audio": audio.name, "response": result})
            entries_after.append(
                api.get(f"/api/v1/sessions/{scratch['id']}/entries").raise_for_status().json()["data"]
            )
    finally:
        api.delete(f"/api/v1/sessions/{scratch['id']}")

    # 5. What each client's summary says after 1..6 clips.
    clip_summaries = record_clip_summaries(api, clients, entries_after)

    # 6. Plan dictation: transcribe, then parse — the same two calls the plan form makes.
    plan_audio = make_clip(PLAN_CLIP, "plan", args.voice_dir)
    plan_transcript = post_audio(api, "/api/v1/transcribe", plan_audio)["transcript"]
    plan_parsed = api.post(
        "/api/v1/plans/parse", json={"text": plan_transcript}, timeout=60,
    ).raise_for_status().json()["data"]
    print(f"plan: {plan_transcript!r} -> {len(plan_parsed['exercises'])} exercises")

    regions, cases = classifier_cases()
    fixture = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "clients": clients,
        "sessions": sessions,
        "entries": entries,
        "plans": plans,
        "session_clips": clips,
        "session_clip_summaries": clip_summaries,
        "brain": brain,
        "session_briefs": briefs,
        "plan_clip": {"audio": plan_audio.name, "transcript": plan_transcript, "parsed": plan_parsed},
        "exercise_regions": regions,
        "classifier_cases": cases,
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=1) + "\n")
    print(f"wrote {FIXTURE_PATH} ({len(sessions)} sessions, {len(entries)} entries, {len(cases)} classifier cases)")


if __name__ == "__main__":
    main()
