# How SuperTrainer Works

A technical walk-through of the code as it is now, from a trainer speaking a voice clip to the card on screen, the summary at the end of a session and the answers the Brain gives.

## The flow at a glance

```
voice clip (m4a) ──> Deepgram transcript                    (services/transcription.py)
                 ──> Claude picks tools: create / modify / clarify   (services/parser.py)
                 ──> names matched, weights in kg, sets checked      (services/validation.py)
                 ──> saved as session entries, cards on the timeline (services/voice.py)
                                        │
session ends ──> AI summary (services/session_summary.py) · workout label (services/workout_classifier.py)
                                        │
trainer asks a question ──> the Brain answers from every client's history (services/brain.py)
```

All backend paths below are under `backend/app/` unless they start with another folder.

## 1. The pieces

**Backend** (`backend/`). A FastAPI app (`main.py`) with routers in `api/` and the logic in `services/`. Every route sits under `/api/v1`. It uses one PostgreSQL database through SQLAlchemy's async engine (`database.py`), with Alembic migrations in `backend/alembic/versions/`. Outside services are Deepgram (speech to text) and Anthropic's API, where every Claude call uses the model in `parser.DEFAULT_MODEL`. On startup, `services/model_health.py` sends a one-token request to that model and refuses to start if the model ID doesn't exist; with no API key set it skips the check. Requests run inline: there is no job queue or background worker.

**Who the trainer is.** There is no login yet. `api/dependencies.get_trainer_id` takes the first row in the `trainers` table and caches it. Every route that reads or changes stored data still checks ownership against that one trainer (`validate_session_ownership` and its siblings), so a session, entry or plan belonging to another trainer returns 404.

**Responses.** Successful responses are `{"data": ..., "meta": {...}}`. Errors are `{"error": {"code", "message"}}`, set by the handlers in `main.py`. Lists use cursor pagination (`services/pagination.py`): a cursor is the ID of the last item on the previous page, and results are sorted newest first with the ID as a tiebreaker.

**Mobile app** (`mobile/`). Expo and React Native with Expo Router, so screens are files in `mobile/app/`: the tabs (today's sessions, clients, the Brain), `recording/[sessionId].tsx` for a live session and `plans/form.tsx` for writing a plan. Server data goes through TanStack Query hooks in `mobile/src/hooks/`, and `mobile/src/api/client.ts` is the single wrapper around `fetch`. Recording uses `expo-av` and produces m4a files (`src/hooks/useVoiceRecorder.ts`).

**Web demo** (`mobile/src/demo/`). The same app built for the browser with no backend behind it. Section 10 covers it.

## 2. A voice clip, end to end

1. **Recording.** On the recording screen the trainer taps the mic, speaks, and taps stop. `useVoiceClipUpload` posts the file as multipart form data to `POST /sessions/{id}/voice-clip`, with the type `audio/mp4`.
2. **Checks at the door** (`api/voice.py`). The session must belong to the trainer, the audio type must be on an allowed list, and the file must be non-empty and at most 25 MB. The client's preferred weight unit is loaded, for clips that give a weight without a unit.
3. **Transcription** (`services/transcription.py`). Deepgram's Nova-3 model transcribes the clip with punctuation and smart formatting on. It is also given a list of keyterms, words Deepgram should listen for. The list is gym jargon (RPE, AMRAP, superset and so on), then abbreviations from the exercise database (RDL, OHP), then multi-word exercise names, capped at 100. Plain words Deepgram already gets right, like "squat" or "row", are left out. A silent clip returns an empty transcript and stops there.
4. **Parsing, validation and saving** (`services/voice.py`, `_parse_and_persist`). The session's existing entries are loaded and passed to the parser as context (section 3). Its output goes through validation (section 4), then new cards are saved and modifications are applied to earlier cards.
5. **Back on the phone.** The response lists the entries created and modified, any clarifications, validation warnings, the transcript, Deepgram's confidence and how long each stage took. The app refetches the session's entries so the new cards appear on the timeline.

**Order is kept.** The parser records the order in which Claude called its tools, and cards are saved in that order, so an observation spoken between two exercises sits between them on the timeline. Each card gets the next `sequence_order` number for the session.

**Typed entries.** `POST /sessions/{id}/text-entry` runs the same steps without Deepgram. The app uses it from the clarification prompt ("Type it out"), in `src/components/Timeline.tsx`.

**Plan dictation** uses `POST /transcribe`, which returns Deepgram's text and saves nothing (section 6).

## 3. How the parser decides: create, modify or clarify

`services/parser.py` sends the transcript to Claude with tool use. Tool use means Claude is given a set of named forms, each with a JSON schema, and answers by filling one or more of them in. The request sets `tool_choice` to `any`, so Claude must call at least one. The tool it picks is the decision, and the filled-in form is the structured data. There are three tools:

- **`record_exercise_card`**: a new exercise. It has the name as spoken, a list of sets (reps, plus optional weight, unit, RPE, RIR, duration, equipment note and per-set notes) and coaching cues. RPE is the rate of perceived exertion, effort on a 1–10 scale. RIR is reps in reserve, how many more reps the client could have done.
- **`record_observation_card`**: a note that isn't an exercise, such as mood, energy or pain mentioned between exercises. It needs a text, a flag colour and a short flag reason. The colours are red (pain, injury, safety), yellow (something to watch), green (a good sign or a neutral check-in) and `clarification`.
- **`modify_exercise_card`**: a change to an earlier exercise. It names the target entry by number, an action (`add` or `correct`), which sets to change (all of them if left out), field updates, extra sets to append and extra cues.

**Session context.** When the session already has entries, the message to Claude starts with a numbered list of them (`format_session_context`), for example `[1] Exercise: Goblet squats | Sets: 3x10 reps @ 16kg`. Claude refers to an entry by that number when it modifies one. With no context, the prompt says never to modify.

**The rules** (`PARSER_SYSTEM_PROMPT`). The main ones:

- **Clarify instead of guessing.** If the transcript isn't training content ("hello testing", random words), or it's unclear which of two similar exercises the trainer means, Claude must write a clarification card. A dubious exercise card is never the right answer.
- **Keep the trainer's words.** The exercise name stays as said ("bench" stays "bench"), and weights stay in the unit spoken. Matching and conversion happen later, in code.
- **Never invent.** A missing weight is left out, never assumed to be bodyweight or 0. Nothing is added that the trainer didn't say. The one exception is "same as before", which copies the previous set's numbers but never its notes.
- **Expand shorthand.** "3 sets of 10 at 80 kilos" becomes three set records. A recap like "first set 60 kilos 10 reps, second set 60 kilos 8" is one card with two sets.
- **Modify instead of duplicating.** "Second set, 8 at 85" for an exercise already logged appends a set to that card. "Also RPE 8 on those" adds to it. `correct` is only for explicit corrections ("no wait", "actually", "that should be").
- **Where comments go.** Anything said during an exercise (form, how a set felt, pain) goes in that set's `notes`. A standalone remark is an observation, and it isn't tied to an exercise unless the trainer names one. Equipment changes ("with a red band") are an equipment note on the set, not a new card.
- **Observation wording.** Observations are written as short clinical notes ("Lower back pain.") and, when there is context, say where in the session they came ("energy dropping after clamshells and squats").

**What happens to each result** (`services/voice.py`):

- **New cards** are saved as entries.
- **Clarification cards** are never saved. They go back in the response as `clarifications_needed`, and the app shows them only when the clip produced no other card. The trainer can then speak again or type the entry.
- **Modifications** are applied to the target entry. Field updates overwrite those fields on the chosen sets, `add_sets` appends sets, and cues are appended. Total volume, the sum of reps times weight, is recalculated. A target number outside the session, or one that points at an observation, is skipped with a warning.

## 4. What validation does

`services/validation.py` sits between the parser and the database. It has no database access, and it reports problems as warnings rather than errors, so a clip with one odd value still saves the rest.

- **Exercise names.** Each spoken name is matched to a canonical name, the one standard name the database uses for an exercise (section 5). The spoken name is kept as `exercise_name` and the match is saved as `exercise_canonical`. No match means a `no_match` warning and an empty canonical name.
- **Weights.** Every weight is stored in kilograms, rounded to 0.1. Pounds are multiplied by 0.453592. A weight with no unit takes the client's preferred unit. The original number and unit are kept on the set as `weight_original` and `weight_unit_original`. A negative weight is made positive, and anything over 500 kg gets a warning.
- **Reps and duration.** These must be positive whole numbers; a zero or negative value becomes 1 with a warning. More than 100 reps gets a warning.
- **RPE and RIR.** RPE is clamped to 1–10 and RIR to 0–10, and a number sent as text is converted. If only RIR is given, RPE is filled in as 10 minus RIR. If both are given and differ by more than half a point, the RIR-derived RPE wins.
- **Observation links.** An observation that points at an entry number outside the session has the link cleared. So does a set number with no exercise, or one below 1.
- **Pain mentions.** Observation text is scanned for a pain word ("sore", "tweaked", "popped") and a body part in the same clause, with negations such as "no knee pain" or "feels better" skipped, and a severity is guessed from modifiers like "slight" or "sharp". These mentions are computed but nothing saves them yet, and injury flags are not created from voice clips.

## 5. The exercise database and matching

The exercise database is one JSON file, `data/exercise_db.json`. Each exercise has a canonical name, aliases (other names trainers use, such as "RDL" for Romanian Deadlift), a category (compound, isolation, plyometric, conditioning or bodyweight), primary and secondary muscles, equipment, difficulty and common form errors. The file is the source at runtime: Deepgram's keyterms, name matching and workout labels all read it. The seed script also copies it into the `exercises` table, but no running code reads that table.

**Matching** (`match_exercise_name`). Every canonical name and alias, lowercased, goes into one lookup. An exact match scores 100. Otherwise rapidfuzz's `WRatio` (a fuzzy string score from 0 to 100 that tolerates typos, word order and partial matches) picks the closest name, and any score of 40 or more is accepted. The confidence is returned but nothing downstream uses it, so a weak match is saved like a strong one. The app shows the spoken name on the card, and the canonical name is used for workout labels, personal bests and the text the summary and the Brain read.

## 6. Data model: sessions, entries and plans

The tables are in `models.py`.

- **Trainer** has clients, sessions and plans.
- **Client** has a name, contact details, goals (a list), injury history (free text), a preferred weight unit (`kg` by default) and an `archived` flag.
- **Session** belongs to a trainer and a client. It has `started_at`, an optional `ended_at` and `scheduled_for`, `duration_minutes`, an optional plan, and `ai_summary`. Ending a session is a `PATCH` with `ended_at`, and the route works out the duration in minutes. Today's list (`GET /sessions?scheduled_for_date=...&tz=...`) converts times to the trainer's time zone before comparing dates.
- **Session entry** is one card. `entry_type` is `exercise_card` or `observation_card`, and `sequence_order` places it in the session. An exercise card has the spoken and canonical names, `sets` (a JSON list, one object per set), `total_volume_kg`, form notes and cues. An observation card has the text, `attached_to_set`, flag colour and flag reason. Entries can also be created, edited and deleted directly (`api/entries.py`). An edit can't set fields that belong to the other card type, and a field sent as null is ignored, so it can't be cleared.
- **Session plan** is a plan for a client's upcoming session. `plan_text` is the trainer's words, `planned_exercises` is the structured version, and `planned_for_date` is optional.
- **Injury flag** records a body part, a pain level from 1 to 10 and whether it has resolved. Flags are created through `api/injury_flags.py` and by the seed script, not by the voice pipeline.

**Older set format.** Voice-logged sets store `weight` and `weight_unit`, while seeded sets store `weight_kg`. Code that reads weights accepts both (`session_summary.set_weight`, `entry_service.update_entry`).

**Plans** (`services/plan_parser.py`, `app/plans/form.tsx`). The trainer types a plan or dictates one. Dictation calls `POST /transcribe`, and then `POST /plans/parse` sends the text to Claude with one forced tool, `record_workout_plan`. That tool returns a workout name and, for each exercise, a cleaned-up name with abbreviations expanded, plus sets, reps and weight as short strings ("10, 8, 6", "20kg"). The trainer can edit the result before saving it with `POST /plans`. Plans are listed on the client's page. The app never attaches a plan to a session, and neither the parser nor the Brain reads plans.

**Unused columns.** The schema has columns nothing writes to yet: 1536-wide vector columns for embeddings (on plans, sessions and entries), `client_analysis`, the Brain conversation tables, and session fields such as `raw_transcript` and `audio_url`. The transcript of a clip is returned to the app and not stored.

## 7. The AI summary

`services/session_summary.py`, served by `POST /sessions/{id}/summary`.

**When it's written.** The app asks for it once the session has ended (`useEndSession`). The route returns 409 if the session hasn't ended. If there's no stored summary, it writes one, saves it on the session and returns it. Later requests return the stored text. A session with no entries gets no summary.

**When it's rewritten.** Every entry create, edit and delete goes through `entry_service`, and each one calls `_clear_summary`, which sets `ai_summary` to null. The next summary request writes a fresh one. On the phone, `useEntryMutations` also drops the cached summary so the screen asks again.

**What Claude is given.** The client's name, goals and injury history, the session length, and every entry in order as one line of plain text (`describe_entry`). Identical sets in a row are grouped ("3 sets of 10 reps at 16kg, RPE 8"). Cues are labelled "timing not recorded", and an observation logged against a set says so. When an exercise has been done in this client's earlier sessions, its line ends with `[previous best: N]`, the heaviest weight in those sessions.

**Rules against inventing things** (`SUMMARY_SYSTEM_PROMPT`). The summary is at most 2–3 sentences and 60 words, covering what was done, how it went and what to remember next time. Claude may state only what the data says, with no invented numbers, feelings, causes or advice. The other rules each close one way it could mislead:

- **Effort.** It may not judge effort ("worked hard") unless an RPE or a note says so.
- **Cues.** It may not say something happened "despite" a cue, because cue timing isn't recorded.
- **Notes.** It may not tie a note to the exercise above it unless the note names that exercise, because notes are listed in time order.
- **Personal bests.** It may call a weight a personal best only when its line shows a previous best and the new weight is higher.

The call uses temperature 0 (the least random setting) and asks for plain text in a trainer's note style, using the client's first name.

## 8. The Brain

`services/brain.py`, served by `POST /brain/ask` and the Brain tab (`app/(tabs)/brain.tsx`). The tab also offers suggested questions from `src/constants/brainSuggestions.json`.

**Context layout** (`build_brain_context`). There is no search step: everything goes into one Claude call, placed in the system prompt after the rules. It starts with a roster section that lists every active client with their goals and injury history, so a question about all clients can't miss one. Then each client gets a section with their profile again and every session, oldest first. Each session is labelled by how long ago it was ("Session 3 days ago, 45 min"), with "(in progress)" if it hasn't ended, and its entries are listed underneath in the same one-line format the summary uses. Archived clients are left out. Stored session summaries are not included.

**Rules** (`BRAIN_SYSTEM_PROMPT`):

- **Data only.** Answer only from the data, and say so in one sentence when the data doesn't cover it. Never state a cause, plan, trend or advice the data doesn't state, and treat repeated identical notes as "steady", not "improving".
- **Short.** At most 120 words, leading with the answer and then the numbers behind it.
- **Plain style.** Relative times ("last week"), never calendar dates. The trainer's terms ("Bench press 3x5 at 80kg"). Plain text, though short "- " lists are allowed.
- **Pain.** Mention pain or injury when it matters to the question. For a question about several clients, check every client's injury history.
- **Placement.** Keep each detail with the session it was listed under. For "now" or "today", use the most recent sessions.

The call uses temperature 0. One question gets one answer: nothing is saved and earlier questions in the chat aren't sent. An Anthropic API error comes back as a 502 with a plain message.

## 9. Workout labels

`services/workout_classifier.py`. Each session in an API response carries a `workout_type` such as "Lower Body" or "Upper Body Push". It isn't stored. `session_service.to_responses` works it out on every read from the session's canonical exercise names, so the label is always current after an edit.

1. **One region per exercise** (`exercise_region`). An exercise in the conditioning category is "conditioning". Otherwise each primary muscle is mapped to push, pull, legs or core by keyword (for example "pectoralis" is push and "biceps femoris" is legs), and the exercise counts toward the region most of its muscles map to.
2. **Count the regions.** Exercises with no canonical name, or none of whose muscles map, are skipped. If nothing is left, the label is "Session".
3. **Pick the label.** If one region has at least 70% of the exercises, the label is that region's name. If push and pull together have at least 70% and both appear, it's "Upper Body". Anything else is "Full Body".

## 10. The web demo and how it's recorded

The demo at https://supertrainer-demo.vercel.app is the real app built for the web with `EXPO_PUBLIC_DEMO=1` (`npm run export:demo` in `mobile/`).

**The switch.** `src/demo/config.ts` reads the variable. `src/api/client.ts` then uses `demoFetch` from `src/demo/server.ts` instead of `fetch`, and `useVoiceRecorder` uses `src/demo/useDemoRecorder.ts` instead of the microphone. `app/_layout.tsx` wraps the app in `DemoFrame`, which shows it in a phone-sized frame on wide screens with short instructions alongside. Every screen is the same code as the phone app.

**The fake backend** (`src/demo/server.ts`). `demoFetch` has `fetch`'s signature and answers the same `/api/v1` routes with the same response shapes. The plain data routes copy the backend's rules: pagination order, 404s for missing items, the plan-must-match-client check, null fields skipped on edit, duration on end, total volume, and the time-zone date filter. Data lives in `src/demo/store.ts`, a copy of the recorded data kept in the visitor's `localStorage` (or in memory when storage is blocked). It is replaced when a newer recording is deployed, and seeded session times are moved to plausible gym hours.

**The replayed parts.** These need Deepgram or Claude, so they replay recorded results:

- **Voice clips.** Recording plays the next of six sample clips. The upload returns what the real pipeline returned for that clip, after waiting as long as the real call took. Clip 4 corrects clip 3, and the demo tracks which live entry each recorded entry became so the correction lands on the right card.
- **Summaries.** Seeded sessions carry their real summaries. A visitor's session gets the summary Claude wrote for the same client after the same number of clips. Editing an entry doesn't clear it, since only recorded summaries exist.
- **The Brain** answers only the suggested questions, with the real Brain's recorded answers.
- **Plans.** Plan dictation returns the recorded transcript and parse. Typed plans and typed entries return an error explaining the demo can't run the parser.
- **Workout labels** come from `src/demo/classify.ts`, a copy of the counting step. Each exercise's region is computed by the backend and stored in the recording.

**Recording it** (`backend/scripts/export_web_demo.py`). The script runs against a freshly seeded local backend (`python -m app.seed`, then uvicorn). In order, it:

1. Moves all seeded dates so the newest session is today, so "3 days ago" is the same in the Brain's answers and on screen.
2. Asks for a summary for every finished session, then asks the Brain each suggested question.
3. Speaks the six clips with macOS `say` (or uses real recordings given with `--voice-dir`) and sends them through the real voice-clip route in a scratch session.
4. For every client, builds a session holding the first one to six clips' entries and records its summary.
5. Dictates a sample plan through `/transcribe` and `/plans/parse`.

It writes everything, with timings, to `mobile/src/demo/fixture.json` and the audio to `mobile/public/demo/`. It also writes test cases for the label classifier, with the backend's own answers, so the demo's copy can be checked against them.

## 11. Testing

**Backend** (`backend/tests/`, run with `pytest` from `backend/`).

- **Database.** Tests use a real PostgreSQL database, the `postgres-test` service in `docker-compose.yml` on port 5433, set by `test_database_url` in `config.py`. It runs the pgvector image because the models declare vector columns. `tests/conftest.py` creates every table once per run from the models (not from migrations) and empties all tables after each test.
- **Requests.** API tests call the app in-process through httpx's ASGI transport. The database dependency is swapped for the test session, and `trainer_for_api` creates a trainer and sets it as the current one.
- **Outside services.** Deepgram and Anthropic are mocked in the default run. The tests check when they're called, what they're sent and what happens with their answers.
- **Real calls.** Tests marked `smoke` call the real Anthropic API and are excluded by default (`pytest.ini`); run them with `pytest -m smoke`.

**Mobile** (`npm test` in `mobile/`, Jest with ts-jest). These cover the set and plan helpers in `src/utils/`, and the demo: the fake backend's routes and rules, the store, the suggested questions, and the label classifier against the backend's recorded cases.

## 12. Where things live

- `backend/app/api/`: the routes, plus `dependencies.py` for the current trainer and ownership checks.
- `backend/app/services/voice.py`: the voice and text pipeline, saving cards and applying modifications.
- `backend/app/services/transcription.py`: Deepgram, keyterms and loading the exercise file.
- `backend/app/services/parser.py`: the three tools, the context format and the parser rules.
- `backend/app/services/validation.py`: name matching, units, set checks and pain detection.
- `backend/app/services/session_summary.py`, `brain.py`, `workout_classifier.py`, `plan_parser.py`: the summary, the Brain, workout labels and plan parsing.
- `backend/app/data/exercise_db.json`: the exercise database.
- `backend/app/seed.py`: demo clients and their history.
- `backend/scripts/export_web_demo.py`: records the web demo's data.
- `mobile/app/`: screens. `mobile/src/hooks/` and `mobile/src/api/`: data fetching. `mobile/src/demo/`: the web demo.
