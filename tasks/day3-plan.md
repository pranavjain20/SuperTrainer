# Day 3: Intent Classification + Additive Parsing + Session Context

## The Big Picture

Day 2 gave you the foundation: tool_use is how we get structured data out of Claude. Tool name = classification, tool schema = the form Claude fills in. Two tools, two types of output.

Day 3 extends that pattern. The question today: **what happens when the trainer isn't saying something new — they're updating something they already said?**

A trainer records "bench press 3 sets of 10 at 80 kilos." Then 30 seconds later: "also, RPE 8 on those." That second clip isn't a new exercise — it's adding information to the bench press that already exists in the session.

Right now our parser would have no idea. It sees each clip in isolation. It would probably try to create some confused exercise card or a vague observation. Today we fix that by:

1. Giving the parser **memory** — it sees what's already logged in the session
2. Teaching it to **classify intent** — "is this new, or is this modifying something existing?"
3. Having it output **structured modifications** — "add RPE 8 to the bench press sets"

## What You'll Learn

- **How to evolve a tool schema** — Day 2 was designing from scratch. Day 3 is adding capabilities to an existing system without breaking it. Same skill you'd use adding features to any API.
- **Context window management** — How to give an LLM the right context to make good decisions. Too little context = can't resolve references. Too much = noise and confusion. This is one of the core skills in AI engineering.
- **Intent classification through tool design** — Instead of building a separate classifier, we encode intent directly in the tool choices. You'll understand why this is cleaner and where the limits are.
- **Backward compatibility** — Everything we build today must not break the existing 30 parser tests. Old behavior stays identical. New behavior layers on top.

## How You're Involved

This is collaborative like Day 2. We design together, and you make the key decisions. Specifically:

- **Part 1 (Session Context):** You'll decide how to format prior entries for Claude. I'll explain the trade-offs (structured JSON vs readable text vs system prompt vs user message), you pick.
- **Part 2 (Modify Tool):** You'll design the tool schema. I'll walk you through the decisions — what fields does it need? How does Claude say "I'm targeting the bench press, not the squats"? How do you handle "RPE 8 on sets 2 through 4" vs "RPE 8 on all sets"? You'll write the schema, I'll explain what's working and what's not.
- **Part 3 (Prompt Rules):** You'll draft the new rules for the system prompt. Day 2 taught you how rules prevent failure modes — today you'll practice writing them yourself for the new behaviors.
- **Part 4 (Tests):** We write tests together. You'll think through: what should we test? What are the edge cases?

The goal: by end of day, you can explain to anyone how intent classification works through tool design, how to give an LLM context, and how to evolve an AI system incrementally.

## Build Order

### Part 1: Session Context (~45 min)

**Concept:** The parser currently receives just a transcript string. We need it to also receive "here's what's already happened in this session." This is the parser's memory.

**What we'll do:**
- Discuss where context belongs (system prompt vs user message) and why
- Design the format together — how should prior entries look to Claude?
- Write `format_session_context()` — a function that turns session entries into a readable context block
- Update `parse_transcript()` to accept a `session_context` parameter
- Write 3-4 tests for context formatting

**Decision point — where does context go?**
- **User message (recommended):** System prompt = behavior/rules (static). User message = per-request data (dynamic). Session context changes every clip, so it belongs in the user message. Keeps the line clean between "how to behave" and "what to process."
- **System prompt:** Could argue context is "background knowledge." But it would grow with every clip and mix static rules with dynamic data.

**Decision point — format?**
- **Structured readable text (recommended):** `[1] Exercise: bench press | Sets: 3×10 @ 80kg | Form: good depth` — compact, Claude reads it naturally, each entry has an ID number Claude can reference.
- **Raw JSON:** Precise but verbose, wastes tokens.
- **Narrative text:** Natural but no clear IDs for Claude to reference back to.

### Part 2: Modify Tool Schema + Dataclasses (~60 min)

**Concept:** This is the big one. We add a third tool — `modify_exercise_card` — so Claude can express "I'm updating something that exists" vs "this is brand new." The design decisions here are the meat of Day 3.

**What we'll do:**
- Explain the design space: what does this tool need to express?
- Design the schema — field by field, with guidance
- Key decisions:
  - How does Claude identify which exercise to modify? (entry ID from context vs exercise name)
  - Should "add info" and "correct a mistake" be the same tool or different?
  - How does targeting work? ("all sets" vs "set 3" vs "sets 2 through 4")
- Build the `ParsedModification` dataclass
- Update `ParserResult` to include modifications
- Wire into `_extract_parser_result()`
- Write 5-6 tests

### Part 3: System Prompt Rules (~30 min)

**Concept:** The tool schema defines WHAT Claude can output. The prompt rules define WHEN and HOW to use each tool. Day 2 had 10 rules. Today we add 3-4 more for the new behaviors.

**What we'll do:**
- Explain what failure modes the new rules need to prevent
- Draft the rules, then refine
- Key rules: when to use modify vs record, how to resolve references from context, what to do when a reference can't be resolved
- Write 3-4 tests for the new rules

### Part 4: Integration Tests + Edge Cases (~30 min)

**What we'll do:**
- Intent classification tests (new vs modify vs observation)
- Mixed transcripts (new exercise + modification in same clip)
- Edge cases: empty context, ambiguous references, unknown exercises
- Full backward compatibility check

## Not In Scope Today

- **Applying modifications to the database** — the parser outputs "add RPE 8 to bench press." Actually merging that into the stored entry is Day 5 (endpoint logic).
- **Fuzzy exercise name matching** — if the trainer says "bench" and context has "bench press," matching those is Day 4 (validation layer). Parser preserves raw names.
- **Weight/unit inference** — "same weight" meaning 80kg is handled naturally by Claude from context, but formal normalization is Day 4.

## Files
- `backend/app/services/parser.py` — all new code
- `backend/tests/test_parser.py` — all new tests

## Verification
- All 396 existing tests still pass (backward compatible)
- ~20-25 new tests pass
- `parse_transcript("bench 10 reps")` still works without context

## Plan Transcript

If you need the full planning conversation for additional context:
`/Users/pranavjain/.claude/projects/-Users-pranavjain-Desktop-supertrainer/5c216a01-e173-4e6f-88f9-2de0fa12d1e3.jsonl`
