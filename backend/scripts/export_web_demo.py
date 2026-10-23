"""Record real backend output for the web demo (mobile/src/demo).

The web demo has no server. It replays what this script records from a real
local backend: the seeded clients and sessions, plus the real Deepgram + Claude
results for a few sample voice clips. Visitors see genuine pipeline output.

Run against a freshly seeded local backend (macOS only: clips use `say`):
    python -m app.seed
    uvicorn app.main:app --port 8000
    python scripts/export_web_demo.py

Writes mobile/src/demo/fixture.json and mobile/public/demo/*.m4a.
Calls Deepgram and Claude once per clip (a few cents in total).
"""

import argparse
import itertools
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.transcription import load_exercise_db  # noqa: E402
from app.services.workout_classifier import classify_workout, exercise_region  # noqa: E402

MOBILE = Path(__file__).resolve().parents[2] / "mobile"
FIXTURE_PATH = MOBILE / "src" / "demo" / "fixture.json"
AUDIO_DIR = MOBILE / "public" / "demo"  # the web export serves public/ at the site root
VOICE = "Samantha"

# One session's worth of clips, in the order a trainer would say them.
# Clip 4 corrects clip 2, which exercises the parser's modify path.
SESSION_CLIPS = [
    "Goblet squats, three sets of ten at sixteen kilos. The last set was an RPE of eight.",
    "Romanian deadlifts, three sets of eight at twenty five kilos. "
    "Hamstrings felt tight on the last set.",
    "Knees caved in a little on the last few squat reps. Cue knees out next time.",
    "Actually, that last set of deadlifts was thirty kilos, not twenty five.",
    "Push ups, three sets of twelve, bodyweight.",
    "Plank, three rounds of forty five seconds.",
]
PLAN_CLIP = (
    "Next session is legs. Back squats four sets of eight at sixty kilos, "
    "walking lunges three sets of ten each side, and leg press three sets of twelve at one hundred kilos."
)


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


def make_clip(text: str, name: str) -> Path:
    """Speak `text` into mobile/public/demo/<name>.m4a."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIO_DIR / f"{name}.m4a"
    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "clip.aiff"
        subprocess.run(["say", "-v", VOICE, "-r", "175", "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(out)], check=True)
    return out


def post_audio(api: httpx.Client, path: str, audio: Path) -> dict:
    files = {"audio": (audio.name, audio.read_bytes(), "audio/mp4")}
    return api.post(path, files=files, timeout=60).raise_for_status().json()["data"]


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    args = parser.parse_args()
    api = httpx.Client(base_url=args.api)

    # 1. Snapshot the seeded data before the script adds anything.
    clients = get_all(api, "/api/v1/clients")
    sessions, entries, plans = [], [], []
    for client in clients:
        client_sessions = get_all(api, f"/api/v1/clients/{client['id']}/sessions")
        sessions += client_sessions
        plans += get_all(api, f"/api/v1/clients/{client['id']}/plans")
        for s in client_sessions:
            entries += api.get(f"/api/v1/sessions/{s['id']}/entries").raise_for_status().json()["data"]

    # 2. Run each session clip through the real pipeline, in order, in one scratch session.
    scratch = api.post(
        "/api/v1/sessions",
        json={"client_id": clients[0]["id"], "started_at": datetime.now(timezone.utc).isoformat()},
    ).raise_for_status().json()["data"]
    clips = []
    try:
        for i, text in enumerate(SESSION_CLIPS, start=1):
            audio = make_clip(text, f"clip-{i}")
            result = post_audio(api, f"/api/v1/sessions/{scratch['id']}/voice-clip", audio)
            print(f"clip {i}: {result['transcript']!r} -> "
                  f"{len(result['entries_created'])} created, {len(result['entries_modified'])} modified")
            clips.append({"audio": audio.name, "response": result})
    finally:
        api.delete(f"/api/v1/sessions/{scratch['id']}")

    # 3. Plan dictation: transcribe, then parse — the same two calls the plan form makes.
    plan_audio = make_clip(PLAN_CLIP, "plan")
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
        "plan_clip": {"audio": plan_audio.name, "transcript": plan_transcript, "parsed": plan_parsed},
        "exercise_regions": regions,
        "classifier_cases": cases,
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=1) + "\n")
    print(f"wrote {FIXTURE_PATH} ({len(sessions)} sessions, {len(entries)} entries, {len(cases)} classifier cases)")


if __name__ == "__main__":
    main()
