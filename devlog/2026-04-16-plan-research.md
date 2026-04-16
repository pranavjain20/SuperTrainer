# Apr 16, 2026 — Plan Creation: Research & Design Thinking

---

## The Problem

Every trainer I've talked to writes plans before sessions. Open the notebook, flip to the client's page, jot down what they're doing today. Squats 4x8 60kg. RDLs 3x10. Hip thrusts 3x12. Done. Maybe 30 seconds for a full session plan.

Every competitor app replaces this with a structured form builder: pick exercise from library → enter sets → enter reps → enter weight → repeat. The #1 complaint across all of them — too many clicks to add a single exercise. Writing "Squats 4x8 60kg" in a notebook takes 2 seconds. In an app form builder, it takes 15-30 seconds. Multiply that by 6-8 exercises per session, 5-6 clients per day. The math doesn't work. That's why trainers stick with notebooks — they're faster for the input step, and the input step is the whole job.

So I spent time researching how every major platform handles this.

---

## Competitive Research

### TrueCoach

Text-based builder with autocomplete from a 3,500+ exercise library. Desktop-first design. They recently added an AI Program Builder where you type a text description and it generates a structured program. The general sentiment: "feels more like a PDF than a modern platform." The text-based approach is actually closer to what trainers want than most competitors realize, but TrueCoach wraps it in enough UI friction that the advantage gets lost.

### Trainerize (ABC Trainerize)

Drag-and-drop builder. No copy-paste of workouts between clients. User reviews consistently mention crashes — "crashes 2-3 times per workout" is a real quote. "Incredibly slow to load." The mobile app "lacks several desktop features," which is a problem when trainers are standing in a gym, not sitting at a desk. The gap between desktop and mobile is a recurring theme across the whole category.

### Everfit

Drag-and-drop with sections. Two methods for adding exercises: drag from library or search-and-add. They market themselves as having the "fastest drag-and-drop builder on the market," which might be true, but that's like being the fastest horse-drawn carriage. Users still report a high number of clicks to get a workout programmed. The fundamental interaction model — select exercise, fill fields, repeat — is the bottleneck, and no amount of drag-and-drop polish fixes it.

### PT Distinction

The most sophisticated builder I found. Batch editing, copy-paste across workouts, multi-workout page view. Described as "significantly faster for serious programming." This is the one that seems to understand that trainers who program for 20+ clients need workflow speed, not pretty animations. Still a form builder at its core, but at least it respects the power user.

### TrainHeroic

Structured builder with 1,300+ exercises in the library. Strong group/team features — makes sense given their focus on strength & conditioning coaches with large rosters. Straightforward and functional. Nothing remarkable about the creation flow, nothing terrible either.

### Hevy Coach

Modern drag-and-drop with a muscle distribution visual that shows which muscle groups the workout targets. Desktop-first for creation. The muscle distribution chart is a nice touch for the client-facing side, but it doesn't solve the creation speed problem. You still have to build the workout exercise by exercise.

### FitBudd

AI-first approach: input client goals, AI generates the plan, deliver to client. Claims "10 plans in 15 minutes." This is interesting because it's the closest anyone's gotten to removing the form builder entirely. But it's a batch generation tool, not a creation tool — it generates programs in bulk from high-level goals. A trainer who wants to write a specific plan for a specific session still can't just say what they want.

### Gymkee

Auto-fill sets/reps from previous sessions, 12 workout formats, claims ~5 minutes per session vs 30 minutes manually. The auto-fill is smart — if the client did squats 4x8 at 60kg last time, pre-populate that. But you're still in a form builder. You're just editing pre-filled forms instead of empty ones.

---

## Common Friction Points

After going through all of them, the same complaints keep surfacing:

1. **Too many clicks to add an exercise.** This is the #1 issue across every single app. The fundamental interaction — select exercise, enter sets, enter reps, enter weight, confirm — has too many steps.
2. **Desktop-first creation, mobile-second.** Trainers are in a gym. They're on their feet. A desktop-first workflow means they either plan at home (extra unpaid work) or deal with a crippled mobile experience.
3. **No copy-paste / poor templating.** If Client A and Client B are both doing push/pull/legs, you'd think copying a workout would be trivial. It's not, on most platforms.
4. **Slow and buggy apps.** Multiple apps (especially Trainerize) get called out for crashes and load times. When you're between clients and have 2 minutes, a 10-second load time is a dealbreaker.
5. **Can't capture qualitative context.** Trainers have notes in their heads — "she complained about her knee last week," "he's been sleeping poorly." Notes fields exist but they go into a black hole. No app connects qualitative observations to the plan.
6. **Per-client pricing kills scaling.** Most platforms charge per active client. A trainer with 40 clients is paying $150-200/month. That's a real barrier, especially for independent trainers.
7. **Feature bloat / steep learning curves.** These apps try to be everything — CRM, billing, nutrition, messaging, scheduling, programming. A trainer who just wants to write plans and track sessions has to navigate a maze.

---

## Why Trainers Stick with Notebooks

It's not that trainers are technologically illiterate. It's that notebooks are genuinely better at the core task:

- **Speed.** "Bench 4x8 @185" — 2 seconds on paper, 15-30 seconds in an app. Paper wins by 10x on the most frequent action.
- **Flexibility.** Paper captures anything. A quick sketch of foot placement. An arrow connecting two exercises as a superset. A circled note that says "ASK ABOUT KNEE." No app handles unstructured information this gracefully.
- **Zero learning curve.** Open notebook. Write. Close notebook. No onboarding, no tutorials, no "how do I add a superset?"
- **Presence.** A clipboard and pen feels professional. A phone feels like you're texting. Multiple trainers have told me their clients comment when they're on their phone too much. The notebook is socially acceptable; the phone isn't.

---

## The Gap We Found

**No major trainer platform uses voice for plan creation.**

Every AI feature in this space is text-input based. FitBudd generates programs from typed goals. TrueCoach's AI Program Builder takes typed descriptions. No app lets a coach speak a plan and have it structured automatically.

The closest analog is on the consumer/athlete side. The Ray app lets users say "135 for 8" during a workout to log sets by voice. But that's athlete-side logging during a session, not coach-side planning before one. The trainer-side tooling hasn't touched voice at all.

This is the gap. Voice is the natural interface for trainers — they talk all day. They explain exercises, cue form, motivate clients. Speaking "legs day, squats 4x8 at 60, RDLs 3x10, hip thrusts 3x12" is faster than writing it and massively faster than tapping through a form builder. Nobody is doing this.

---

## Our Approach: Natural Language Input → AI Parsing → Structured Output

The key insight took a while to crystallize, but it's simple once you see it:

**Trainers are comfortable with the OUTPUT format (structured exercise lists). They're uncomfortable with the INPUT method (structured forms). We replace the input with natural language and keep the output the same.**

Every competitor tries to make the form builder faster — better autocomplete, drag-and-drop, templates, auto-fill. They're optimizing the wrong thing. The form builder IS the problem. You don't make it faster; you remove it.

### How it works

1. Trainer types or speaks naturally: "Legs day, squats 4x8 at 60, RDLs 3x10, hip thrusts 3x12"
2. Deepgram (with gym keyterm prompting) handles voice → text
3. Claude parses the natural language → structured exercises with compact prescriptions
4. Output shown in a familiar compact format — editable inline
5. Trainer reviews, edits any rows directly, saves

### Why this beats the notebook on BOTH dimensions

The notebook wins on input speed. Apps win on organization. Nothing currently wins on both. Our approach does:

- **Less friction than paper:** Plan is auto-linked to the client, dated, stored, searchable. No flipping through pages to find what Elena did three weeks ago.
- **Faster than form builders:** Speaking or typing natural language is faster than tapping through fields. It's also faster than handwriting for most people.

The trainer gets the speed of a notebook with the organization of an app. That's the pitch.

### Why Deepgram specifically

I considered whether we even need our own transcription, or whether something like Wispr Flow (a consumer dictation app that replaces the keyboard) would work. It wouldn't:

- **Wispr Flow is a consumer keyboard replacement, not an API.** You can't integrate it into a backend pipeline. It types into whatever text field has focus. We need server-side transcription that feeds into our parsing pipeline.
- **Deepgram supports keyterm prompting.** We already have 142 exercise names and gym jargon terms boosted in our existing voice pipeline. "RDL" doesn't become "our deal." "Sumo deadlift" doesn't become "sumo dead lift." This matters enormously for accuracy.
- **Pipeline architecture:** Deepgram is the ears (speech → text), Claude is the brain (text → structured output). Clean separation. We already built this pipeline for session recording in Phase 1b — plan creation reuses the same infrastructure with a different prompt.

---

## Design Decisions

### Natural language is the input method

Not a form builder. Not dropdowns. Not drag-and-drop. The trainer writes or speaks what they want, and the AI structures it. This is the core bet.

### Voice AND text

Both input methods, same parsing pipeline. Some trainers will prefer typing a few lines. Some will prefer speaking. Some will use voice in the gym and text at their desk. We offer both and let usage data tell us which people actually prefer. No need to pick one now.

### Edit the output, not the input

After the AI parses the plan, the trainer sees a structured list. If the AI got something wrong — misheard a weight, wrong rep count — they tap the row and fix it inline. No re-parse round-trip. No "try saying it again." If the AI gets 90% right, fix the 10% directly.

This is important because re-parsing is slow and unpredictable. Editing structured output is fast and predictable. The trainer should never feel like they're fighting the AI.

### Prescription as display string

For v1, we store "4x8 @ 60kg" as a string, not decomposed into sets/reps/weight fields. The text row IS the data. This is deliberately simple:

- It matches how trainers think and write
- It avoids complex schema for something that's inherently freeform ("4x8-10 @ 60-65kg" doesn't fit neatly into integer fields)
- It's easy to display, easy to edit, easy to understand
- We can always decompose later if we need structured analytics on planned vs actual

### Separate transcription endpoint

`POST /api/v1/transcribe` returns text only. Decoupled from the session recording pipeline. The session pipeline does transcription + parsing + entry creation in one flow. Plan creation separates these steps because the trainer needs to see and approve the parsed output before it's saved. Different workflow, different endpoint.

### Plan parser is a new Claude service

The plan parser gets a different prompt than the session transcript parser. Session parsing extracts what happened (past tense, observed performance). Plan parsing extracts what should happen (future intent, prescribed targets). The output schema is similar but the interpretation is different:

- Session: "He did squats, 4 sets of 8 at 60kg" → exercise card with performed sets
- Plan: "Squats 4x8 at 60kg" → plan entry with target prescription

Different prompts, different validation, shared infrastructure.

---

## What Real Trainers Actually Write

I looked at what trainers actually put in their notebooks (and what they type in apps when given free-text fields). They don't write prose plans. They write short lists:

```
Squats 4x8 60kg
RDL 3x10 40kg
Hip thrusts 3x12
Leg press 3x10
```

That's it. Maybe 4-8 lines. No paragraphs. No explanations. Observations and context live in their head — they remember that the client's knee was bothering them, they don't write it in the plan.

This means:

- **Text input is actually fast.** A few short lines, typed in 15-20 seconds. The form builder overhead is the problem, not the amount of information.
- **Voice can also be fast.** Speaking that list takes maybe 10 seconds. If the AI cleans up the output accurately, voice is the fastest option.
- **The app wins on organization and context, not input speed.** The real value isn't making plan creation 2 seconds faster — it's that the plan is linked to the client, dated, searchable, and eventually connected to what actually happened in the session. That's what paper can't do.

---

## Where This Goes

The immediate build is straightforward: text input field, voice button, parse with Claude, show structured output, let trainer edit and save. That's the v1.

But the reason this matters beyond v1 is that it establishes natural language as the primary interaction model. If plan creation works well with "just tell me what you want," then plan modification works the same way ("swap out squats for leg press, keep everything else"), and eventually The Brain can generate plans conversationally ("what should I do with Elena today given her knee issue?").

The form builder is a dead end. Natural language scales.
