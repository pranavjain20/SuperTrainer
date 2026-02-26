# Phase 1b — The Voice Pipeline

This is where the AI starts. Phase 1a built the database and API that stores training data. Phase 1b built the system that *creates* that data from a trainer's voice.

---

## The Big Picture

A trainer is mid-session with a client. They pull out their phone and say: "Elena did 3 sets of leg press, 55 kilos, 10 reps each. Good form on set 1 and 2, slight hip shift on set 3."

Five seconds later, that voice clip has become structured data in the database — an exercise card with 3 sets, a canonical exercise match to "Leg Press (Machine)," and an observation card about the hip shift attached to set 3.

Here's the full flow:

```
Trainer speaks into phone
    ↓
[1] Deepgram (transcription.py) — turns sound into text
    ↓  "Elena did 3 sets of leg press, 55 kilos..."
    ↓
[2] Claude Parser (parser.py) — turns text into structured cards via tool_use
    ↓  { exercise: "leg press", sets: [{reps: 10, weight: 55, unit: "kg"}, ...] }
    ↓
[3] Validation (validation.py) — normalizes and cleans the structured data
    ↓  fuzzy match "leg press" → "Leg Press (Machine)", convert lbs→kg, detect pain
    ↓
[4] Voice Endpoint (voice.py) — orchestrates the chain, persists to database
    ↓
Structured SessionEntry in database
```

The intelligence split is deliberate: **Deepgram is the ears** (transcribes sound to text, no understanding). **Claude is the brain** (understands what the trainer meant, structures it). **Validation is the safety net** (catches what Claude gets wrong, normalizes messy data). Each layer has one job and does it well.

---

## Component 1: Deepgram — The Ears

**File:** `backend/app/services/transcription.py`

Deepgram is a speech-to-text API. We send it raw audio bytes, it sends back text. It's a black box — we don't control how it transcribes, we just control what hints we give it.

### The One Clever Thing: Keyterm Prompting

Deepgram has a feature where you can send up to 100 "keyterms" — words it should listen extra hard for. Think of it as a cheat sheet. Without it, Deepgram might hear "Romanian deadlift" and transcribe "Romanian dead lift" or "roman and dead lift." With the keyterm, it knows that exact phrase exists and is more likely to get it right.

We have 142 exercises with 3,466 aliases. We can only send 100 terms. So we prioritize:

1. **Gym jargon first** (RPE, AMRAP, superset, deload) — words that don't exist in normal English. Deepgram has zero chance without help.
2. **Abbreviations next** (RDL, OHP, GHR) — short all-caps strings that could be anything.
3. **Multi-word exercise names last** (Romanian deadlift, lat pulldown) — compound phrases Deepgram might split wrong.

We skip common single words like "squat," "bench," "curl" — Deepgram already knows these from normal English. No point wasting a slot.

### What Comes Out

A `TranscriptionResult` with:
- `transcript` — the text Deepgram heard
- `confidence` — how sure it is (0.0 to 1.0)
- `duration_seconds` — how long the audio was
- `words` — individual words with timestamps and per-word confidence

The transcript text is what gets passed to Claude next. The word-level data is stored for potential future use (highlighting which part of the audio maps to which exercise).

---

## Component 2: Claude Parser — The Brain

**File:** `backend/app/services/parser.py`

This is where 80% of the engineering effort went. The parser takes a text transcript and outputs structured exercise cards, observation cards, and modifications to existing entries. The mechanism is **tool_use**.

### The Core Insight: Tool Name = Classification

The traditional approach would be two steps: (1) ask Claude "is this an exercise or observation?", then (2) ask Claude to extract the structured data. Two API calls, two prompts to get right.

We do it in one step. We define three tools — `record_exercise_card`, `record_observation_card`, and `modify_exercise_card` — and Claude decides which to call based on what it hears. **Which tool Claude calls IS the classification. The tool's input schema IS the structured output.** One API call does both.

The key line is `tool_choice={"type": "any"}` — this forces Claude to call at least one tool. It can't just respond with text. It *must* fill in a form. And the API guarantees the output matches the schema — you never get malformed JSON.

### The Three Tools

Each tool is a JSON schema — a "form" Claude fills in.

**Tool 1: `record_exercise_card`** — For new exercises. Fields: exercise_name (required, preserved exactly as spoken), sets array (each set has reps, weight, weight_unit, rpe, rir, equipment_note, duration_seconds), form_notes, cues_given. Notice the description says "preserve exactly as the trainer said it" — Claude shouldn't normalize "bench" to "barbell bench press." That's validation's job later.

**Tool 2: `record_observation_card`** — For observations about the session or a specific exercise/set. Fields: observation_text (required), flag_color (red/yellow/green for severity), flag_reason, target_entry_id (which exercise it's about), attached_to_set (which specific set). The target fields enable set-level observation attachment — if a trainer says "left knee pain on set 3 of squats," the observation gets linked to that exact set.

**Tool 3: `modify_exercise_card`** — For corrections and additions to already-recorded exercises. Fields: target_entry_id (which entry to modify), action ("add" or "correct"), target_sets (which sets to change, or all), updates (the field changes), plus form_notes/cues_given to append. This enables the trainer to say "RPE 8 on those" or "no wait, 85 not 80" and have it applied to the right entry.

### The System Prompt — 23 Rules, Each Preventing a Specific Failure

The tool schemas define WHAT the output looks like. The system prompt defines HOW to fill it in. Every rule exists because without it, Claude made a specific mistake during testing:

- **Rule 3** — "Preserve the exercise name EXACTLY." Without this, Claude helpfully rewrites "bench" as "barbell bench press," which breaks fuzzy matching downstream.
- **Rule 7** — "Only include data the trainer actually said." Claude loves to hallucinate reasonable-sounding RPE values. This stops that.
- **Rule 8** — "If ambiguous, yellow flag it." Better to flag uncertainty than guess wrong. Yellow-flagged observations get returned to the trainer as `clarifications_needed` instead of being saved.
- **Rule 15** — "Use 'correct' only when the trainer explicitly signals a correction." Without this, Claude would overwrite data any time it saw something similar. "Add" is the safe default.
- **Rule 19** — "Standalone observations have NO target_entry_id." This is the Day 6 distinction: "lower back is hurting" (session-level, no attachment) vs "lower back pain on set 3 of deadlifts" (attached to specific exercise and set). The signal is whether the trainer explicitly names an exercise in the same breath.
- **Rule 23** — "Include temporal context in session-level observations." Instead of "energy dropping," Claude writes "energy dropping after clamshells and squats" — making the observation self-explanatory without checking the timeline.

### Session Context — How Claude Sees Prior Entries

When the trainer sends their second, third, fourth clip in a session, the phone sends the prior entries along with the audio. The parser formats those into readable text that Claude can reference:

```
Session context (3 entries logged so far):
[1] Exercise: Barbell Back Squat | Sets: 3×10 reps @ 100kg | Form: good depth
[2] Observation: Client seems energetic today (green flag: positive session start)
[3] Exercise: Romanian Deadlift | Sets: 3×8 reps @ 80kg
```

Claude sees this and can reason: "the trainer said 'RPE 8 on those' — they probably mean entry [3], the most recent exercise." It calls `modify_exercise_card` with `target_entry_id=3`. If the reference is ambiguous (two similar exercises in context), Rule 13 tells Claude to yellow-flag it instead of guessing.

### The Data Classes — Immutable Snapshots

The output of parsing is a set of frozen (immutable) dataclasses: `ParsedExerciseCard`, `ParsedObservationCard`, `ParsedModification`, wrapped in a `ParserResult`. Once Claude extracts data, it's a snapshot that can't be accidentally modified downstream. Tuples instead of lists for the same reason — the parser's output is a fact about what was said, not something to be edited.

### How `parse_transcript()` Works

The main function ties it all together:
1. Validates the transcript isn't empty
2. Formats session context (if provided) into the readable block above
3. Sends one message to Claude: system prompt + tools + user message (context + transcript)
4. Iterates through Claude's response content blocks, building dataclasses from each `tool_use` block
5. Returns the `ParserResult` with all extracted cards and modifications

Malformed tool calls (missing required fields, empty dicts) are silently skipped but preserved in `raw_tool_calls` for debugging. This makes the parser resilient to occasional Claude misbehavior without crashing the pipeline.

---

## Component 3: Validation — The Safety Net

**File:** `backend/app/services/validation.py`

Validation sits between the parser and the database. It takes raw parser output (exercise names as spoken, weights in original units, unstructured observations) and normalizes everything: fuzzy-matches exercises to the canonical DB, converts weights to kg, validates set data, and extracts structured pain mentions from observation text.

### Design Principles

These are stated at the top of the file and matter:

- **Pure functions, no DB access.** Validation loads the exercise DB from JSON, doesn't touch PostgreSQL. This makes it fast, testable, and stateless.
- **Warnings, not exceptions.** A bad weight doesn't crash the pipeline — it warns and continues. Partial results are useful. The voice endpoint decides what to do with warnings.
- **No modification of parser dataclasses.** Consumes read-only parser output, produces its own output types. Clean data flow with no mutation.

### Job 1: Exercise Fuzzy Matching

Claude preserves the exercise name exactly as spoken ("bench", "RDL", "lat pull down"). Validation matches it to our canonical DB of 142 exercises with 3,466 aliases.

Two-step approach:
- **Exact match first** (O(1) dict lookup) — "bench press" maps directly to "Barbell Bench Press"
- **Fuzzy match fallback** — uses rapidfuzz's WRatio scorer against all 3,466+ keys. "lat pull down" fuzzy-matches to "lat pulldown" alias → "Lat Pulldown (Cable)" canonical name

The score cutoff is 40 (out of 100). Below that, it returns no match and warns. The voice endpoint uses the confidence score to decide: high confidence → auto-apply the canonical name, low → warn the trainer.

### Job 2: Weight Normalization

Internally we store everything in kg. If the trainer said "185 pounds," validation converts: `185 × 0.453592 = 83.9 kg`. If they said "80 kilos," it stays 80.0 kg. If no unit was mentioned, it uses the client's `preferred_weight_unit` — a per-client setting we added because trainers with clients in different countries need this.

Both values are preserved: `weight_kg` for the database, `weight_original` + `weight_unit_original` so the trainer sees what they actually said.

### Job 3: Pain Extraction

When an observation says "client reported sharp lower back pain," validation extracts structured data:
- **Body part**: "lower back" → standardized to `"lower back"`
- **Severity**: "sharp" → maps to severity 7 (out of 10)
- **Raw text**: the original sentence for context

The pipeline: quick reject (no pain keyword in text → skip entirely), split into clauses, check each clause for pain keywords AND body parts. Skip negated clauses ("no knee pain", "doesn't hurt anymore"). Deduplicate by body part, keeping the highest severity.

73 body part terms (including spine regions, muscles, joints, digits), 65 pain keywords (including sounds like "pop/crack/snap" and states like "gave out/buckled"), 30 severity modifiers. All with word-boundary regex to avoid false positives like matching "shin" inside "shining" or "pull" inside "pulldown."

#### Why Pain Extraction Is Rule-Based, Not AI

This is a deliberate architectural decision worth understanding — it applies to many AI product choices.

**Speed.** The pipeline has a ~3-5 second budget. Claude is already called once for parsing (~2.9s average). A second Claude call for pain extraction would nearly double latency. Rule-based extraction runs in microseconds.

**Cost.** Every Claude call costs money. Pain extraction runs on every observation card. At scale (hundreds of sessions/day), a second API call per observation adds up. Regex costs nothing.

**Determinism.** "Sharp lower back pain" should extract the same structured data every single time — body part: lower back, severity: 7. Rule-based guarantees that. Claude might classify the same sentence slightly differently across runs. For safety-critical data (pain/injury tracking that informs future session planning), you want zero randomness.

**The problem is simple enough.** Trainers don't speak in poetry about pain. They say "sharp knee pain" or "lower back is hurting" or "shoulder feels tight." The linguistic pattern is narrow: pain keyword + body part + optional severity modifier. That's a pattern matching problem, not a comprehension problem.

**Claude already does the hard part.** The parser flags red/yellow observations when it hears pain — that's the comprehension step (understanding the trainer's intent). Validation just extracts structured fields (which body part, how bad) from text that's already been identified as pain-related. Complementary layers, not redundant ones.

**The general principle: use AI where you need understanding, use rules where you need pattern matching.** Knowing which parts of your system need intelligence and which don't is a real architectural skill. Over-applying AI is expensive, slow, and non-deterministic. The best AI products use AI surgically — only where simpler approaches can't do the job.

### Job 4: Set Validation

Range checks and normalization: reps > 100 gets a "suspicious" warning. Weight > 500kg gets flagged. Negative weight → absolute value + warning. RIR gets converted to RPE if no RPE was provided (`RPE = 10 - RIR`). If both RIR and RPE are present and disagree, validation trusts RIR (it's the more direct measurement) and warns about the conflict.

---

## Component 4: The Voice Endpoint — The Glue

**Files:** `backend/app/services/voice.py` (orchestration) + `backend/app/api/voice.py` (HTTP layer)

This is where the three components chain together. The service runs the pipeline; the router handles HTTP concerns.

### The Pipeline — Five Steps

```python
async def process_voice_clip(db, session_id, client_id, audio_data, mime_type, default_weight_unit):
    # Step 1: Transcribe (Deepgram)
    transcription = await transcribe_audio(audio_data, mime_type=mime_type)

    # Step 2: Load session context from DB
    existing_entries = await entry_service.list_entries_by_session(db, session_id)
    context_dicts = [_entry_to_context_dict(e) for e in existing_entries]

    # Step 3: Parse (Claude)
    parser_result = await parse_transcript(transcript, session_context=context_dicts)

    # Step 4: Validate (fuzzy match, weight conversion, pain extraction)
    validation_result = validate_parser_result(parser_result, ...)

    # Step 5: Persist to database
    # ... create entries, apply modifications, collect clarifications
```

Each step is timed with `time.perf_counter()` — the response includes `transcription_ms`, `parsing_ms`, `validation_ms`, `persistence_ms` so you can see exactly where the time goes. Average total: ~3 seconds, with parsing (~2.9s) dominating.

### The Clarification Decision

Yellow-flagged observations are the parser saying "I'm not sure what this means." These do NOT get saved to the database. They're returned as `clarifications_needed` in the API response — the mobile app shows them to the trainer, who can clarify or dismiss.

Red observations (pain, injury, safety) and green observations (PRs, milestones) get persisted normally. Only yellow (ambiguity) gets held back. This is a product decision: **ambiguity should surface to the trainer, not silently become bad data.**

### How Modifications Work

When the parser says "update entry [3]," the voice service:
1. Looks up the actual DB entry at that index position
2. Validates it's an exercise card (can't modify observations this way — Rule 14)
3. Builds update kwargs: merges set-level changes into existing sets, appends form_notes/cues
4. Saves via `entry_service.update_entry`

The `_build_modification_kwargs` function handles the merge logic. For "add" actions, new data goes alongside existing data. For "correct" actions, new data overwrites targeted fields. Form notes and cues are always appended regardless of action type — you never lose coaching notes.

### The Context Loop

Step 2 loads existing entries from the database, not from the mobile client. The server is the source of truth. The phone could be offline, manually edited, or out of sync — the server always loads fresh context before parsing. This is part of the stateless design: the phone sends audio, the server handles everything else.

### The Router — Thin by Design

The API router (`api/voice.py`) handles HTTP concerns only:
- Ownership validation (same chain as every other endpoint: session → client → trainer)
- MIME type check (12 supported audio formats including WAV, MP3, M4A, WebM)
- File size limit (25 MB — generous for voice clips)
- Loads the client's preferred weight unit before calling the pipeline
- Formats the response in the standard `{"data": ..., "meta": {}}` wrapper

All business logic lives in the service. The router is just plumbing.

---

## How It All Fits Together — A Full Example

Let's trace a real scenario end-to-end. A trainer is mid-session with Elena. They've already recorded two exercises. Now they pick up the phone and say:

> "She did 3 sets of leg press, 55 kilos, 10 reps each. Good form on sets 1 and 2, slight hip shift on set 3."

Here's exactly what happens:

**1. Phone sends audio** → `POST /api/v1/sessions/{id}/voice-clip` with the audio file as multipart form data.

**2. Router validates** → Checks the session exists, belongs to this trainer, audio is a valid type and under 25 MB. Loads Elena's preferred weight unit (kg).

**3. Deepgram transcribes** → Raw audio becomes text: "She did 3 sets of leg press, 55 kilos, 10 reps each. Good form on sets 1 and 2, slight hip shift on set 3."

**4. Context loads** → The server queries the DB and finds 2 existing entries: `[1] Exercise: Barbell Back Squat | Sets: 3×10 reps @ 100kg` and `[2] Exercise: Romanian Deadlift | Sets: 3×8 reps @ 80kg`.

**5. Claude parses** → Receives the context + transcript. Makes TWO tool calls:
- `record_exercise_card(exercise_name="leg press", sets=[{reps:10, weight:55, weight_unit:"kg"}, {reps:10, weight:55, weight_unit:"kg"}, {reps:10, weight:55, weight_unit:"kg"}], form_notes=["good form on sets 1 and 2"])`
- `record_observation_card(observation_text="slight hip shift on set 3", flag_color="yellow", flag_reason="form concern on set 3", target_entry_id=3, attached_to_set=3)`

Wait — target_entry_id=3? That's the entry that WILL be created from this same clip. The observation is about the leg press, which is being recorded right now. Actually, Claude is smart enough to know that the context has 2 entries, so this new exercise will be [3]. But in practice, since both come from the same clip, the observation card either uses the target from context (if it's about a prior exercise) or goes session-level. The specifics depend on the transcript.

**6. Validation runs** →
- Fuzzy matches "leg press" → "Leg Press (Machine)" (exact alias match, confidence 100)
- Weight: 55 kg stays 55 kg (Elena's preferred unit is kg)
- Total volume: 3 × 10 × 55 = 1,650 kg
- Observation: checks target_entry_id is in range, extracts pain? No pain keywords in "hip shift" — no PainMention generated. (If she'd said "hip pain on set 3," validation would extract body_part: "hip", severity: 5.)

**7. Persistence** →
- Exercise card → new SessionEntry (entry_type=exercise_card, sequence_order=3, exercise_canonical="Leg Press (Machine)")
- Yellow observation → NOT persisted. Returned as `clarifications_needed` so the trainer can confirm the hip shift concern.

**8. Response** → JSON with the created entry, the clarification, timing breakdown, and any warnings. The mobile app shows the exercise card in the timeline and a prompt asking about the hip shift.

Total time: ~3 seconds. The trainer barely looked away from Elena.

---

## Testing — 683 Tests

Phase 1b added 377 tests on top of Phase 1a's 306. Here's how they break down:

### Exercise DB Tests (36 tests)
Validates the 142-exercise database: structural quality (every exercise has required fields), comparative metrics (alias count, muscle coverage), trainer speech recognition (common spoken names all have aliases), keyterm coverage (all gym jargon terms present).

### Transcription Tests (24 tests)
Deepgram service with mocked API responses. Tests the keyterm priority algorithm, skip terms, abbreviation detection, empty audio handling, error paths.

### Parser Tests (75 tests)
Core parsing (30), intent classification + modifications (37), observation attachment (8). All use mocked Claude responses — we construct the exact tool_use content blocks Claude would return, so tests are deterministic and don't hit the API.

### Validation Tests (119 tests)
Fuzzy matching, weight normalization, pain extraction (keywords, body parts, severity, negation, clause splitting), set validation (ranges, RIR→RPE conversion, suspicious values), observation attachment validation (target_entry_id range, orphan set numbers, no-context handling).

### Voice Pipeline Tests (42 tests)
End-to-end integration with both Deepgram and Claude mocked. Happy path, modification updates, clarification handling, 404/422 errors, empty transcripts, timing fields, weight unit conversion, mixed content clips (exercise + observation in same clip), data integrity (sequence ordering, volume calculation, canonical match).

### Live Tests (25 scenarios)
Real Claude API calls (not mocked). 9 real trainer quotes, 6 synthetic patterns, 5 observation attachment scenarios, 5 adversarial edge cases. All 25 pass. These live in `backend/scripts/test_pipeline_live.py` — a separate runner from the test suite since they hit external APIs.

---

## Key Architecture Decisions

### Why Stateless?

The server has no memory of the session between clips. Each clip gets the full context loaded from the DB. This means:
- **Offline works.** Trainer records 5 clips without signal. Phone sends them all when back online. Each one processes against the DB state at that moment.
- **Manual edits work.** Trainer manually fixes a set count in the app between clips. Next clip's context includes the fix.
- **Crash recovery works.** Server restarts mid-session? No problem — next clip loads fresh context.
- **Race conditions handled.** Two clips sent simultaneously? Each one loads its own snapshot.

### Why Split Service and Router?

`voice.py` (service) has the pipeline logic. `api/voice.py` (router) has HTTP logic. This means:
- The pipeline is testable without HTTP (pass a mock DB session, get back a VoiceClipResult)
- If we ever need the pipeline from a different trigger (scheduled batch processing, WebSocket), the service works unchanged
- HTTP concerns (MIME validation, size limits, response formatting) stay in one place

### Why Frozen Dataclasses Throughout?

Every intermediate result (TranscriptionResult, ParsedExerciseCard, ValidatedExerciseCard, VoiceClipResult) is a frozen dataclass. Data flows forward: transcription → parser → validation → persistence. No step modifies a previous step's output. This makes bugs nearly impossible — if the data is wrong, you know exactly which step produced it.

### The Intelligence Split

This is the most important architectural concept in the pipeline:

| Component | Intelligence | Why |
|-----------|-------------|-----|
| Deepgram | None (black box) | Transcription is a solved problem. We don't add value here. |
| Claude Parser | High (prompt engineering) | Understanding speech intent requires real comprehension. This is where we add value. |
| Validation | Low (rules) | Pattern matching, not understanding. Regex is faster, cheaper, deterministic. |
| Voice Service | None (orchestration) | Just wiring. No decisions. |

The moat is in the Claude layer — specifically, the 23 system prompt rules and the 3-tool schema design. That's what makes SuperTrainer understand trainer speech better than a generic AI transcription service.

---

## Quick Reference — Phase 1b Files

| File | Purpose |
|------|---------|
| `data/exercise_db.json` | 142 exercises, 3,466 aliases, expert common_errors |
| `services/transcription.py` | Deepgram STT + keyterm prompting |
| `services/parser.py` | Claude tool_use parser (3 tools, 23 rules) |
| `services/validation.py` | Fuzzy matching, weight normalization, pain extraction |
| `services/voice.py` | Pipeline orchestration + persistence |
| `api/voice.py` | HTTP endpoint for voice clips |
| `scripts/test_pipeline_live.py` | 25 live Claude scenarios |
| `tests/test_transcription.py` | 24 Deepgram tests |
| `tests/test_exercise_db.py` | 36 exercise DB quality tests |
| `tests/test_parser.py` | 75 parser tests |
| `tests/test_validation.py` | 119 validation tests |
| `tests/test_voice.py` | 42 pipeline integration tests |

### Numbers

- 4 pipeline components
- 3 Claude tool schemas, 23 system prompt rules
- 142 exercises, 3,466 aliases
- 73 body parts, 65 pain keywords, 30 severity modifiers
- 683 total tests (306 Phase 1a + 377 Phase 1b)
- 25/25 live scenarios passing
- ~3 second average pipeline latency
