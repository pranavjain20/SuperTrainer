# SuperTrainer — Product Requirements Document

**Version:** 3.0
**Date:** February 19, 2026
**Author:** Pranav Jain
**Status:** Active Development

---

## What Changed from V1 and Why

Version 1 was written with monetization as a core lens. After deeper thinking, this version reflects a more honest framing.

**The project is now primarily a portfolio and research artifact** — a real, working product that demonstrates deep understanding of the AI + health + fitness space, with genuine utility for trainers. If trainers love it and it grows, monetization can follow. The goal for the next 2-2.5 months is to build something impressive, real, and used by real trainers who say it helped them.

**What this changes:**
- Billing (F14) is deprioritized — it exists in the full feature list but is not in scope for the initial build
- Features are tiered by what can deliver value before real user data exists, versus what requires longitudinal data to mean anything
- The intelligence layer must be genuinely impressive, not just functional
- Optimize for "trainers say it helped them" not "trainers pay for it"

**What does NOT change:**
- The full technical architecture, data model, API design, and build plan from V1 are preserved
- All original features remain in the full feature list — nothing is deleted, only reprioritized
- TDD approach, testing standards, and quality bar remain identical

---

## The Core Insight

The difference between Alcaraz's trainer and the trainer of an average gym-goer is not knowledge or care — it is cognitive bandwidth. Alcaraz's trainer has one client. The average Equinox trainer has 25. That trainer cannot hold 25 people's full context simultaneously. They forget what happened last Tuesday with client #12. They miss the pattern that a client's knee pain correlates with heavy squat weeks. They walk into sessions underprepared.

AI removes this constraint. Not by replacing the trainer's judgment — the trainer's physical instincts, real-time assessment, and coaching relationships cannot be replicated — but by giving every trainer the memory, pattern recognition, and preparation infrastructure of a dedicated one-on-one coach.

**A key design principle that runs through everything:** The AI should never overstate what the data supports. Early in a client relationship, the AI surfaces observations. It does not generate plans or make confident predictions. As data accumulates over months, the intelligence deepens. The product earns trust by being honest about what it knows.

---

## Vision

Give every personal trainer the memory, pattern recognition, and preparation of a coach with a single dedicated client.

**One-liner:** "The intelligence infrastructure that turns every trainer into an elite coach."

**This is NOT:** A workout logger. A scheduling tool. A CRM. A plan generator. Those exist. We are the intelligence layer that makes trainers better at the actual work of coaching.

---

## Target User

**Primary:** Independent personal trainers and Equinox-caliber gym trainers with 20-40 active clients.

They charge $100-150/session, see 8-10 clients/day. Their clients are typically 40-60 year old professionals — well-to-do, health-conscious, complex injury histories. These are not athletes. They are returning-to-fitness adults who have a lot at stake: old injuries, sedentary periods, work stress affecting recovery. Their trainer genuinely cares but is stretched thin across too many clients.

The trainer currently uses Notes, Google Sheets, or nothing. They are not technical. The product must work in 30 seconds per interaction, not 5 minutes.

---

## Core Loop

```
Trainer records session (voice)
    → AI transcribes each clip in real time
    → AI extracts structured data (exercises, sets, weights, observations, pain)
      — displayed as a live timeline on screen as trainer speaks
    → Trainer reviews + confirms (30 seconds)
    → Data saved to client history

Before next session:
    → Calendar integration surfaces upcoming session proactively
    → AI generates pre-session context (adaptive to data maturity)
    → AI flags patterns (progression, pain, form degradation)
    → Trainer walks in prepared

During and after sessions:
    → Conversational agent answers questions about any client, any time
    → Cross-client queries surfacing fleet-level intelligence
```

---

## Full Feature List

All features we want in an ideal world. Priority order defined in the next section. Nothing here is deleted — features are either in scope for the initial build or deferred to later phases.

**Tier 1 — Core:**
1. Voice-to-Structured-Session
2. Pre-Session Context
3. Conversational Agent

**Tier 2 — Makes It Complete:**
4. Trainer Home Screen + Client Profile + Session History
5. Calendar Integration

**Tier 3 — Intelligence Layer (requires real data to be meaningful):**
6. Pattern Detection
7. Injury Risk Scoring
8. Plan Co-Creation

**Tier 4 — Growth and Moat:**
9. Client App + Wearable Integration
10. Progress Charts
11. Session Sharing
12. Authentication & Multi-Trainer
13. Billing
14. Offline Support
15. ML Injury Prediction
16. Exercise Database (community)
17. Client Portal

---

## Priority Tiers — Build Order

### Tier 1 — Core (Build First, Must Work Perfectly)

These features make the product worth existing. If these do not work well, nothing else matters. These can all be built and demonstrated before having real users, using synthetic data.

1. **Voice-to-Structured-Session** — The foundation. Everything else depends on data existing.
2. **Pre-Session Context** — The daily value. The thing that makes a trainer open the app every day.
3. **Conversational Agent** — The wow moment. What makes this feel fundamentally different from a logging tool.

### Tier 2 — Makes It Complete

4. **Trainer Home Screen + Client Profile + Session History** — The navigation shell. One flow, not three features. Needed before showing this to any real trainer.
5. **Calendar Integration** — Reduces session logging friction dramatically. Trainers already have their schedule in their calendar.

### Tier 3 — Intelligence Layer

6. **Pattern Detection** — Rule-based engine. Requires 4+ sessions per client to be meaningful.
7. **Injury Risk Scoring** — Rule-based weighted formula first, ML later. Requires real longitudinal data.
8. **Plan Co-Creation** — Trainer drives, AI assists. Only meaningful after sufficient session history (6+ months ideally).

### Tier 4 — Growth and Moat

9. **Client App + Wearable Integration** — Client-facing app with Whoop/Oura/Apple Watch OAuth.
10. **Progress Charts** — Visual graphs: weight progression, volume trends, pain frequency, risk score history.
11. **Session Sharing** — Send session summary to client via email/SMS.
12. **Authentication & Multi-Trainer** — Proper auth, multi-trainer support for gyms, gym owner dashboard.
13. **Billing** — Stripe. Free tier, Pro ($199/month), Gym tier ($499/month). Deprioritized for initial build.
14. **Offline Support** — Record audio offline, queue for upload, local cache.
15. **ML Injury Prediction** — Trained model replacing rule-based scoring. Only viable at 500+ clients with real injury outcome data.
16. **Exercise Database** — 500+ exercises with aliases, muscle groups, equipment, common errors, coaching cues.
17. **Client Portal** — Clients see their own training data, progress charts, trainer notes selectively shared.
18. **Client Health Profile** — Single source of truth for everything a trainer needs to know about a client beyond sessions. Blood reports and lab work (uploaded as PDFs/images), body composition scans (DEXA, InBody), medical notes, injury documentation, any health documents the client shares. The brain can reason over all of it — "Pranav's last blood report showed low vitamin D, which can affect muscle recovery." Surfaced from real trainer customer discovery: trainers review blood reports and health data during initial assessments and currently have no single place to store and reference this information.

---

## Feature Deep Dives — Tier 1

### Feature 1: Voice-to-Structured-Session

This is the foundation. Everything else depends on data existing. The voice pipeline is how data gets in.

#### The Core Interaction Model

The trainer's primary input method is voice. Not forms. Not dropdowns. Voice, because trainers will not fill out forms between sets in a gym. The bar for input friction is: it must feel like talking to yourself.

The session stays open from start to finish. The trainer taps a button to speak, says what happened, taps to stop. They do this repeatedly throughout the session — after each set, after an observation, whenever something worth noting happens. They tap End Session when done.

The AI processes each voice clip immediately and updates the session in real time so the trainer can catch misparsing while the information is still fresh. End-of-session batch processing is not acceptable — by then the trainer has forgotten the details.

#### Session Lifecycle

**Before the session (8:55am):**
The app knows from the trainer's calendar that they have a session with Joe in 10-15 minutes. It sends a push notification surfacing Joe's pre-session briefing. Trainer taps the notification, lands directly in the brain with Joe's briefing context pre-loaded.

**Starting the session — two entry points:**
- Calendar-driven: App detects upcoming session from calendar, surfaces it proactively with a Start Session prompt
- Manual: Trainer opens the app, selects a client, taps Start Session

Both lead to the same session screen.

**During the session — the recording interaction:**
The session screen has a large, prominent tap-to-speak button at the bottom. Trainer taps → button activates (visual + haptic feedback) → trainer speaks → trainer taps again to stop → clip is sent for transcription and parsing → structured data appears on screen within 2-3 seconds.

The trainer does not hold the button. Tap to start, tap to stop. This is intentional — more natural than press-and-hold for gym use, and prevents accidental long recordings.

**Why continuous recording was rejected:** Two alternatives were considered and ruled out. (1) Recording the full session continuously — rejected because trainer and client may not be comfortable having the entire conversation recorded, and it creates far too much noise for the AI to parse what is actually important vs. ambient conversation, music, and gym sounds. (2) Requiring the trainer to navigate in and out of a logging screen between sets — rejected because it creates too much friction and breaks the coaching flow. The tap-to-speak model is the deliberate middle ground: intentional, frictionless, private.

**Button visual behavior:** When the trainer taps to start recording, the button visibly expands (grows larger) and changes color or animates to indicate it is live. When the trainer taps to stop, it contracts back to its resting state. This visual expansion/contraction gives unambiguous feedback that recording is active — important in a gym environment where the trainer may not be looking at the screen directly. Haptic feedback accompanies both the start and stop taps.

**What the trainer says — natural language, no rubric:**

The trainer speaks naturally. All of the following are valid inputs:
- "Three sets of squats, 80 kilos, 10 reps each, form was solid"
- "Actually add a note to that — slight forward lean on the last rep"
- "Pranav mentioned his right shoulder feels tight, happened on the third set"
- "Moving on to lunges now"
- "He's looking fatigued today, considering cutting the last exercise"

The AI must handle all of these correctly. Four key capabilities required:

1. **Additive parsing** — A second clip saying "oh, 80 kilos, I forgot" is understood as an addition to the previous exercise entry, not a new entry.
2. **Session state awareness** — The AI maintains running awareness of which exercise is active and which set we're on. "Third set, he felt pain" attaches to set 3 of the current exercise.
3. **Natural language tolerance** — "eight reps" / "8" / "did eight" all mean the same thing.
4. **Intent classification** — Is this clip a new exercise, an addition to current exercise, a set-level note, an exercise-level note, or a standalone observation? AI classifies correctly and places accordingly.

#### The Session Timeline (UI)

The session screen displays a chronological, hierarchical timeline that builds in real time as the trainer speaks. Two types of entries:

**Exercise Cards — Structured:**
Show exercise name, sets, reps, weight. Each set is a row. Notes can attach to individual sets or to the exercise as a whole.

**Observation Cards — Freeform:**
For things that don't attach neatly to a specific exercise. Pain reported between exercises, general fatigue observations, coaching notes about the client's state today. Visually distinct from exercise cards.

The AI decides which type to create based on what the trainer said. If it can attach something to a specific set, it does. If it cannot, it creates an observation card. The timeline order reflects the actual order of the session.

Example timeline structure:
```
[Exercise Card] Squats
  Set 1 — 80kg × 10 reps
  Set 2 — 80kg × 10 reps
  Set 3 — 80kg × 8 reps
    ⚠ Note: Right shoulder discomfort on this set

[Observation Card] Joe mentioned knee tightness between exercises

[Exercise Card] Lunges
  Set 1 — 60kg × 12 reps
  Set 2 — 60kg × 12 reps
  Set 3 — 60kg × 10 reps
```

**Inline editing:** Every field is tappable and editable. Exercise name, weight, reps, notes — all editable inline without leaving the session screen. If the AI misheard something, the trainer fixes it in two taps. Edit rate is tracked as a product health metric — target under 20% of sessions requiring edits.

**Mid-session agent access:** The session screen also provides access to the conversational agent without leaving the session. A secondary button or persistent icon allows the trainer to switch momentarily into agent mode — ask a quick question ("How was Pranav's shoulder last time?" / "What weight was he using for squats three weeks ago?") — get an answer in 2-3 seconds, and return immediately to the recording interface. The session state is preserved throughout. This interaction should take no more than 10-15 seconds and must not disrupt the session flow. See Feature 3 for full agent specification.

#### End Session

Trainer taps End Session. A summary screen appears showing the complete structured session — all exercises, all sets, all observations, all flags highlighted. Trainer reviews, confirms, session is saved to client history.

**Plan dictation for next session:** Before confirming the save, the trainer is prompted: "Anything to note for next time?" This is optional and dismissible. If the trainer speaks or types a response — "Next time we're doing upper body push, focus on shoulder stability" — it is saved to the session_plans table and becomes Section 2 of the pre-session context before the client's next session. This is the primary mechanism for populating the "Today's Plan" section in Feature 2. It belongs here, at End Session, because that is when the trainer's thinking about next time is freshest.

The session summary is the permanent record. It feeds the pre-session context for next time, the pattern detection engine, and the conversational agent.

#### What the AI Must Not Do

- Invent data that was not spoken
- Make confident assertions based on one session ("this client has a knee problem" from one mention of tightness)
- Silently fail — if something is unclear, create a note flagged for trainer review rather than guessing
- Lose track of session state across clips (which exercise is active, which set we're on)

#### Technical Implementation

**STT:** Deepgram Nova-3 with keyterm prompting for gym vocabulary (exercise names, equipment, muscle groups). Handles gym noise. Target 90%+ accuracy on clear speech. If real-world accuracy falls below 80%, investigate lapel mic workflow or post-session recording mode.

**Parsing:** Claude Sonnet with tool_use for reliable structured JSON extraction. System prompt maintains session state across clips — each new clip is sent with the full session context so far so the AI knows where we are. This is stateless on the server — session state is maintained on the client and sent with each request.

**Validation layer:** Rule-based post-processing after LLM extraction:
- Exercise name normalization (maps "squats" / "back squat" / "barbell squat" to canonical name from exercise database)
- Weight unit handling (kg/lbs normalization, stored internally as kg always)
- Implicit set expansion ("3 sets of 10" → 3 individual set records)

**Real-time display:** Each clip processed and displayed within 2-3 seconds of trainer stopping recording.

**Parser test suite:** 15+ real transcript samples covering common patterns. This is a living document — every new edge case found in the wild gets added. Parser accuracy tracked as a continuous metric.

---

### Feature 2: Pre-Session Context

This is the daily value. The thing that makes a trainer open the app every single day. It is not one screen — it is an entire preparation workflow that spans from the night before a session to the moment the trainer walks in.

#### The Core Problem It Solves

A trainer who sees 8 clients a day cannot hold full context on everyone. They forget what happened last Tuesday with client #12. They don't remember that Pranav's knee pain specifically flares after squats. They walk into sessions underprepared. This feature solves that — not in 5 minutes, but in 30 seconds.

---

#### The Two Distinct Modes of This Feature

This feature has two completely different use cases that serve two completely different moments in a trainer's day. They must be designed as separate experiences.

**Mode 1 — Deep Preparation (night before or morning of)**
The trainer has time. They sit down and go through their clients for the day thoughtfully. This is the planning and review moment — unhurried, detailed, comprehensive.

**Mode 2 — The 5-Minute Briefing (right before the session starts)**
The trainer has no time. They're between clients or walking to the gym floor. They need the most important things in 30 seconds. This is a quick-glance, read-only summary — not a planning tool.

These two modes are not the same screen. They serve different moments and must be designed accordingly. Conflating them creates a screen that does neither job well.

---

#### Mode 1: Deep Preparation View

**Entry point:**
When the trainer opens the app in the morning or the night before, the first screen they see is today's session list — a clean, calendar-style view of all clients scheduled for the day with their session times.

**What the session list looks like:**
- Clean list, not cluttered
- Each row: session time + client name
- Each row has two distinct entry points:
  1. **Tap the row** → opens the full client profile (session history, goals, injury history, everything)
  2. **"Today's Plan" button** on the row → opens directly into that client's plan for today, skipping the full profile

The "Today's Plan" shortcut exists specifically for the morning preparation flow where the trainer wants to quickly scan and update plans for multiple clients without navigating through full profiles repeatedly. Less friction.

**Inside the client's plan view:**
The trainer sees the structured workout plan for today's session. They can read it, modify it, add exercises, remove exercises, or dictate changes via voice. The plan is displayed in the same structured exercise card format as a real session — exercise name, sets, reps, weight (where specified). Clean and readable, equivalent to or better than looking at a written program on paper.

---

#### The Planning Flow (How Plans Are Created and Modified)

**Critical principle: The plan and the session log are completely independent.**

The plan is what the trainer intends going in. The session log is what actually happened. These are never coupled. A session does not require a plan to exist. A plan does not get invalidated if the session goes completely differently — and it often will. Clients change their minds. Energy is low. An exercise gets swapped. This is normal and expected. The app must accommodate it without friction.

**Example:** Trainer plans legs — squats, lunges, leg press. Client shows up and says energy is low, wants to do upper body instead. Trainer says fine, they do upper body. The session log reflects what actually happened (upper body). The plan (legs) remains as a record of what was intended. The AI notes the deviation silently as a data point — it does not require the trainer to reconcile the two, flag an error, or update anything. It just knows.

**How the trainer creates a plan:**
Voice input, exactly like the session recording flow. Trainer taps to speak, dictates the workout — "Tomorrow Pranav, squats four sets of eight, Romanian deadlifts three sets of ten, leg press three sets of twelve" — and the AI structures it into exercise cards. Same format as a real session timeline. Clean, structured, readable.

**What the AI does and does not do when creating a plan:**
- It structures exactly what the trainer said. Nothing more.
- If the trainer did not specify weight, the weight field is empty. Genuinely empty — not zero, not a placeholder, not a guess.
- The AI never approximates, infers, or fills in a number based on previous sessions. Never.
- If the trainer wants to know what weight to use, they ask the brain. The brain retrieves it from session history and answers. If the trainer then says "add that," the brain updates the plan. This is always an explicit trainer-initiated action, never automatic.

**Where plans come from — three sources:**
1. Dictated at the end of the previous session (primary mechanism — see Feature 1 End Session section)
2. Created or modified in the deep preparation view the night before or morning of
3. Created manually inside the app at any time

All three lead to the same structured plan that appears in the client's pre-session context.

**The brain assists with planning:**
The trainer can use the conversational agent while in the planning view to fill in details. Examples:
- "What weight was Pranav using for squats last time?" → brain retrieves from session history → trainer says "add that" → plan updated
- "What weight has he been progressing at on deadlifts?" → brain summarizes the trend → trainer decides the weight → trainer dictates it → plan updated
- The brain never proactively fills in the plan. It only responds to explicit asks and acts on explicit instructions.

---

#### Mode 2: The 5-Minute Briefing

**What it is:**
A push notification that fires a set time before the session starts (configurable — default 10 minutes before, not 5 minutes, because 5 minutes is too little time to act on anything). The notification is read-only. Its entire job is to be readable in 30 seconds while the trainer is walking to their client.

**Important note on timing:**
Trainers do not prepare 5 minutes before a session. They prepare the night before, or an hour before, or in the morning. The deep preparation happens in Mode 1. The briefing is not a preparation tool — it is a final mental reset right before walking in. The timing of the notification should reflect this: 10-15 minutes before is enough time to read it and mentally adjust, but not so early that it interrupts Mode 1 preparation.

**Back-to-back sessions problem:**
When sessions are back-to-back, the briefing for session #2 may arrive mid-session #1. The notification should still fire — the trainer can choose to read it or dismiss it. It is not a blocker.

**What the briefing notification contains:**
The notification itself (on the lock screen or notification tray) shows: client name + one-line preview of the single most important thing. That's it. Tapping it opens the full briefing.

**The full briefing — four layers:**

The briefing is structured around four layers, each conditional on data availability. If a layer has nothing meaningful to say, it is hidden entirely. The briefing never fills space with generic text.

**Layer 0 — Today's Plan (always shown if it exists)**
The structured list of exercises planned for today. Brief — exercise names and sets/reps only, not full detail. If no plan has been set, this section shows: "No plan set for today — want to quickly add one?" This nudges the trainer in case they forgot, without blocking them. The briefing fires regardless of whether a plan exists.

**Layer 1 — Last Session (any session, regardless of muscle group)**
Anything notable from the most recent session with this client — regardless of what muscle group was trained. This is about general client state. Examples:
- "Pranav was unusually fatigued last session — energy seemed low throughout"
- "Pranav complained of lower back tightness last session"
- "Pranav hit a PR on bench press last session — great form, high energy"

This layer is not filtered by today's plan. It is about the client as a person going into today. If last session was unremarkable, this layer is hidden.

**Layer 2 — Last Session of Today's Muscle Group**
The last time this client trained the same muscle group or exercises as today's plan. This is more directly relevant because the body has muscle-specific patterns — if Pranav's knees were painful the last time he did squats, that is directly relevant today even if that was three weeks ago.

Example: Today is a leg day. The last leg session was three weeks ago. Layer 2 surfaces what happened in that specific session — "Last leg session: Pranav complained of knee pain after squats, had to reduce weight on lunges."

This layer is only shown if there is a previous session of the same type and it had something notable in it.

**Layer 3 — Trend Flags for Today's Exercises**
The longer-term pattern, but specifically scoped to today's planned exercises. Not generic trends — exercise-specific trends.

The logic: look at today's planned exercises, check the full session history for those specific exercises, surface patterns that are worth knowing going into today.

Examples:
- "Pranav has complained of knee pain in 3 of the last 5 squat sessions — this is a recurring pattern, not a one-off"
- "Pranav's squat weight has not progressed in 8 weeks — worth checking in on today"
- "Pranav's form notes on Romanian deadlifts show increasing lower back strain over the last month"

The AI scores what to surface based on four criteria — all four must be considered together:
1. **Recency** — more recent = more relevant, unless part of a persistent pattern
2. **Severity** — sharp pain outranks mild soreness, significant plateau outranks minor stagnation
3. **Trend direction** — something getting worse is more urgent than something stable
4. **Actionability** — the flag must be something the trainer can actually do something about in today's session. "Client missed two sessions last month" is interesting but not actionable mid-session. "Knee pain recurring after squats" is directly actionable because squats are in today's plan.

The briefing surfaces the top 2-3 flags maximum across all layers. Anything more is a report, not a briefing.

---

#### Tapping the Briefing — Opening the Brain

When the trainer taps the push notification and opens the briefing, they are taken directly into the brain — the conversational agent — not a separate static screen.

The brain has already ingested the briefing content. It knows what was surfaced in that notification. It opens with a prompt that invites the trainer to go deeper: something like "You have Pranav in 10 minutes. Anything you want to dig into?"

The trainer can then ask anything:
- "How many times has he complained about knee pain?"
- "Is it getting worse or staying the same?"
- "What exercises seem to trigger it?"
- "What weight was he using for squats when the pain started?"

The brain answers immediately, citing specific sessions. The trainer reads, forms a mental plan, puts the phone in their pocket, walks in prepared.

**Critical design decision: The brain that opens from the briefing is the full, unrestricted brain.** It is not scoped to just today's client. If the trainer wants to ask about a different client, they can. One brain, always. Scoping it to a single client adds friction and defeats the purpose. The brain's job is to reduce friction — any artificial restriction does the opposite.

---

#### Data Maturity Rules (Enforced in Backend — Not Suggestions)

The briefing adapts based on how much data exists. These thresholds are hard-coded in backend logic:

- **0 sessions:** No briefing. New client. Nothing to surface yet.
- **1 session:** Layer 1 only (last session). No trends, no exercise-specific flags.
- **2-3 sessions:** Layer 1 + Layer 0 (plan if set). No trend analysis yet.
- **4+ sessions:** All layers active. Exercise-specific trend flags start appearing.
- **10+ sessions:** Richer trend analysis. Pain pattern flags with confidence if recurring.

The product never pretends to know more than it does. A flag that appears after 2 sessions carries less weight than one that appears after 15. The AI communicates this — "I've only seen 3 leg sessions, so this may not be a pattern yet" is a valid and honest response.

---

#### Future: Wearable Data Integration (Tier 4)

When the client app and wearable integration exist (Tier 4), a fifth layer is added to the briefing: same-day recovery data from Whoop, Oura, or Apple Watch. "Pranav's recovery score is 42% today — consider reducing intensity or swapping heavy compound movements for accessory work."

This layer only appears when the data exists and is from the same day. It is never estimated or carried over from yesterday. Architecture must support adding this layer without restructuring the briefing system.

---

#### What the Brain Does NOT Do in This Feature

- Generate a plan unprompted. The plan always comes from the trainer.
- Fill in weights or reps the trainer did not specify. Optional means genuinely empty.
- Surface the same flag repeatedly if the trainer has acknowledged it. If the trainer has noted they are aware of the knee pain pattern, the AI should not keep surfacing it as a surprise every session.
- Fabricate insight when there is insufficient data. Empty sections are honest. Generic filler text is not acceptable.

---

### Feature 3: Conversational Agent — The Brain

This is the wow moment. The thing that makes SuperTrainer feel fundamentally different from any logging tool, notes app, or generic AI assistant. This is not a feature inside the app. It is a layer on top of the entire app.

---

#### The Core Philosophy — Why This Exists

A trainer who has been doing this for 15-20 years wakes up at 4am and spends 30 minutes going through their notes before the day starts. They read what happened last session, think about what to do today, form a mental picture of each client. That system works. It has worked for 15 years.

SuperTrainer is not asking them to abandon that system. It is making that system dramatically better by replacing the notes with a brain that remembers everything, never forgets, and can answer any question instantly.

The value proposition is simple and must be true simultaneously:
1. **Less time** than what they do today — not equal time, less
2. **Less friction** than what they do today — voice is the answer, not typing in an app
3. **Better output** than what they do today — the brain knows things the trainer has forgotten

If any one of these three breaks, adoption fails. A 40-45 year old trainer with a working 15-year system will not switch to something that takes more time, adds friction, or produces worse results. All three must be true simultaneously.

**A note on the nature of the problem this product solves:**
This is not a "hair on fire" problem. If it were that urgent, someone would have solved it already. Trainers are getting by fine today. The product does not save them from a crisis — it creates leverage. It makes them meaningfully better at the work they already do well. That is a different kind of value, and it requires a different kind of adoption strategy. The product has to earn its place in a workflow that already works. That means the first experience must be demonstrably better — faster, cleaner, smarter — not just different.

---

#### What the Brain Is

One conversational agent — voice or text — that knows everything about every client and can answer any question, take certain actions, and reason across all data simultaneously. It is not scoped to one client. It is not a different brain for different parts of the app. It is one brain. Always.

The analogy: Gemini on Android — a persistent presence you can summon from anywhere. You don't context-switch into a different tool. You just talk to it.

The brain is Claude — but a version of Claude with two things on top of what Claude already knows:
1. **Deep fitness domain knowledge** — strength training principles, programming, injury patterns, recovery science, biomechanics. Enough to answer questions the way a well-read strength coach would, not a generic chatbot.
2. **Everything about this trainer's clients** — every session ever logged, every plan created, every observation made, every health document uploaded, every wearable data point. All of it.

---

#### Where the Brain Lives in the App

The brain has a permanent, fixed tab in the bottom navigation bar. Same location no matter what screen the trainer is on. One tap from anywhere in the app, always.

The bottom nav structure:
- **Home** — today's sessions
- **Clients** — full client list
- **Brain** — the conversational agent
- **Session** — active session (appears contextually when a session is running)

The icon for the brain tab should feel intelligent and distinctive — visually communicating that this is the smart core of the product, not just another menu item. Exact icon design is a UI decision for later, but it should feel like SuperTrainer's identity, not a generic chat bubble.

The brain does NOT live as a floating button on top of other screens. Floating buttons obscure content and feel like afterthoughts. The brain is not an afterthought — it is one of the four most important things in the product and deserves a permanent seat in the navigation.

---

#### Memory — How the Brain Remembers Everything

The brain never forgets. Every piece of information ever entered into the app is permanently part of the brain's knowledge for that trainer. Sessions logged six months ago. Plans created last week. A pain observation from session 3. A blood report uploaded on day one. All of it.

This is what separates the brain from a generic AI assistant. A generic assistant knows nothing about Pranav. This brain knows everything about Pranav — more than the trainer consciously remembers, because it never forgets and the trainer does.

**The right mental model:** Think of the brain as a custom Claude. Claude already knows a lot about fitness. What makes this brain different is that it also knows everything about Pranav specifically — more about Pranav than any version of Claude on its own ever could, because it has been given every single piece of information the trainer has ever logged about him. It is Claude plus a very detailed, ever-growing notepad about every client. Every session logged adds a note. Every pain observation adds a note. Every blood report uploaded adds a note. Every plan created adds a note. The notepad never gets thrown away. Every question the trainer asks draws from the entire notepad, always.

**Technically how this works:** The brain uses RAG (Retrieval Augmented Generation). When the trainer asks a question, the system fetches the most relevant data from the database and passes it to the brain. The brain reasons over what is retrieved and answers. This is a solved technical problem — it is fast, accurate, and scales to any number of clients and sessions. The context window limitation is handled by smart retrieval, not by limiting what the brain knows.

**One brain per trainer.** Not one brain per client. The brain has access to all clients' data simultaneously and can reason across them. When you ask about Pranav, it retrieves Pranav's data. When you ask it to compare Pranav and Joe, it retrieves both. When you ask which of your 25 clients is at highest injury risk, it retrieves relevant data from all 25.

---

#### Conversation History — Like Claude or ChatGPT

The brain tab has two components:

1. **Current conversation** — starts fresh each time the trainer opens a new thread. Clean, focused, no clutter from previous conversations.

2. **Conversation history** — a repository of all past conversations with the brain, organized as separate threads. Exactly like Claude.ai or ChatGPT — the trainer can scroll back through past conversations, reference something they discussed yesterday, pick up a thread from last week.

Why this matters: a trainer might ask the brain something insightful about Pranav's programming on Monday, and on Wednesday want to reference that conversation. They should be able to find it, exactly like finding a past Claude conversation.

The brain's memory of client data (via RAG) is separate from conversation history. Even if conversation history is cleared or not referenced, the brain still knows everything about every client from the logged data. Conversation history is for the trainer's reference, not for the brain's memory.

---

#### The Three Honest States — Non-Negotiable

This is one of the most important design principles in the entire product. The brain operates in one of three states for any given question, and it must always be transparent about which state it is in.

**State 1 — Full answer: I have both knowledge and client-specific data.**
The brain has general fitness knowledge on the topic AND specific logged data on this client. It gives a contextualized answer that combines both.

Example: "What does low HRV mean for Pranav's training?"
Answer: "Low HRV generally indicates incomplete recovery and elevated stress on the nervous system. For Pranav specifically, his last three sessions with low reported energy all came after high-volume weeks. That pattern suggests his recovery capacity may be the limiting factor — you might consider reducing volume on weeks where his recovery indicators are low."

**State 2 — Partial answer: I have knowledge but not enough client-specific data yet.**
The brain has general fitness knowledge on the topic but insufficient logged data on this specific client to contextualize it. It answers the general question honestly and flags what it doesn't know about the client.

Example: "What does low HRV mean for Pranav's training?" — asked after only 2 sessions.
Answer: "Low HRV generally indicates incomplete recovery and elevated nervous system stress — it usually means reducing intensity or volume that day is wise. I don't have enough data on Pranav yet to tell you how his training responds to low recovery days specifically. Once we have more sessions logged, I'll be able to give you a more personalized answer."

**State 3 — Neither: I don't have enough knowledge or data to answer well.**
The brain doesn't have sufficient knowledge or client data to answer accurately. Rather than fabricating an answer, it offers to look it up.

Example: A highly specific medical question about a rare condition.
Answer: "I don't have enough information to answer that accurately. Want me to look it up?" — the brain triggers a web search and returns a real answer.

**Why this matters more in fitness than anywhere else:**
A hallucinated recipe suggestion from ChatGPT is annoying. A hallucinated insight about a client's injury risk or training load affects a real human body. The trainer makes decisions based on what the brain tells them. A wrong answer — especially a confidently wrong answer — can lead to a client getting hurt.

The brain must never bridge a gap with invention. If the gap exists, it names it. This is not a weakness — it is the feature that makes the brain trustworthy. A trainer who trusts the brain completely will use it constantly. A trainer who gets one wrong answer will never fully trust it again.

**The student analogy for understanding the three states:** Think of a 25 year old who studied data science but also took some psychology courses. They know a lot about data science, less about psychology, and almost nothing about medieval history. When asked a data science question, they give a full confident answer. When asked a psychology question, they give what they know and flag their uncertainty. When asked about medieval history, they say "I don't know enough — let me look it up." That is exactly how the brain should behave. It is not useless about things outside its specialty. It just knows what it knows and is honest about what it doesn't.

The brain should never say "Pranav's recovery seems fine" if it doesn't actually have recovery data on Pranav. It should say "I don't have recovery data on Pranav — connect his wearable or log some observations and I'll be able to tell you more."

---

#### The Brain Takes Actions — Not Just Answers

In V1, the brain answers questions and takes actions specifically around plan creation and modification. This covers the highest-friction use case: the trainer who currently spends 30 minutes at 4am making plans in their notes.

With the brain, that workflow becomes:
- "Let's make Pranav's plan for tomorrow. We'll do squats, lunges, step ups, and barbell rows."
- Brain structures it into exercise cards instantly.
- "What weight was he using for squats last time?"
- Brain retrieves and answers.
- "Add that to tomorrow's plan."
- Brain updates the plan.
- Done. What took 5 minutes of flipping through notes took 60 seconds of talking.

**V1 actions the brain can take:**
- Create a plan for a client
- Modify an existing plan (add exercise, remove exercise, update sets/reps/weight)
- Answer any question about any client

**Vision — full agentic capability (post-V1):**
In an ideal world the brain can take any action in the app that a trainer could take manually. "Mark today's session as done." "Archive this client." "Move Joe's session to Thursday." "Show me all clients I haven't seen in two weeks." Everything voice or text, nothing manual.

This is technically feasible and is the north star. The architecture must be designed from day one to support it. Do not build the brain as a read-only question-answerer and then try to bolt on action-taking later — that is a painful rebuild. Build with agentic capability in mind even if V1 only exposes plan actions.

The 40-45 year old trainer who has used notes for 20 years should eventually not need to navigate any screen manually. They open the app, they talk to the brain, the brain handles everything.

---

#### The Brain Is Reactive — Never Speaks First

The brain does not initiate conversations. It does not send proactive messages. It does not interrupt the trainer with suggestions.

The briefing notification system (Feature 2) handles proactive intelligence. That is a separate system with a separate purpose. The brain is a question-answering and action-taking system. It speaks when spoken to.

This is by design. A brain that talks to you unprompted becomes noise. The trainer decides when they want intelligence. The brain delivers it on demand.

---

#### Cross-Client Reasoning

One of the most powerful things the brain can do that no trainer can replicate manually: reason across all clients simultaneously.

Examples:
- "Which of my clients are showing signs of overtraining?"
- "Who's made the most progress in the last month?"
- "Anyone I haven't seen in over two weeks?"
- "Which of my clients have mentioned knee pain recently?"
- "Compare Pranav and Joe's squat progression over the last three months."

A trainer with 25 clients cannot hold all of that in their head. The brain can retrieve it instantly. This is the fleet-level intelligence that makes the product genuinely irreplaceable.

---

#### Available During Sessions

The brain is accessible mid-session without leaving the session screen. A secondary button on the session screen switches the trainer momentarily into brain mode. They ask a quick question, get an answer in 2-3 seconds, return to recording. Session state is fully preserved throughout. The interaction should feel like 10-15 seconds — quick enough to not disrupt the coaching flow.

---

#### Fitness Domain Knowledge — V1 vs. Vision

**V1:** The brain uses Claude's existing fitness knowledge, which is genuinely good — strength training principles, programming concepts, injury patterns, recovery science. Sufficient for the first 10-50 trainers. If gaps are found in real usage, they will be surfaced through trainer feedback.

**Post-V1 investment:** After beta, if trainers flag knowledge gaps or the brain gives incorrect domain answers, invest in a curated fitness knowledge base — strength training literature, programming textbooks, sports science research, coaching resources. This makes the brain exceptional rather than just good. It is a deliberate post-beta investment, not a V1 blocker. Build it when the evidence says you need it, not before.

---

#### Technical Implementation

- **Architecture:** RAG over a continuously growing per-trainer data store. One brain per trainer. All client data accessible.
- **Model:** Claude Sonnet. No fine-tuning required. Claude's existing knowledge plus strong system prompting plus retrieved client data is sufficient.
- **Retrieval:** PostgreSQL with semantic search. Question analyzed, most relevant data retrieved, passed to Claude as context. Fast enough for real-time conversation.
- **Action-taking:** V1 uses structured tool calls for plan creation and modification. Vision expands tool set to cover all app actions.
- **Conversation history:** Stored in database, organized as threads per trainer. Separate from client data RAG — trainer can reference past conversations, brain always has access to all client data regardless.
- **Response time target:** Under 3 seconds for single-client questions, under 5 seconds for cross-client questions.
- **Honesty enforcement:** System prompt explicitly instructs the brain to identify which of the three states it is in for each answer and to never fabricate client-specific context it does not have.

---

#### What the Brain Must Never Do

- Hallucinate client-specific data it does not have. Ever. For any reason.
- Speak first or send proactive messages — that is the briefing system's job.
- Give a confident answer about a client's health or injury risk when it does not have sufficient data to support that confidence.
- Take irreversible actions without confirmation — before doing something that cannot be undone (archiving a client, deleting data), the brain should confirm with the trainer first.
- Be scoped to a single client — one brain, all data, always.

---

## Feature Deep Dives — Tier 2

### Feature 4: Trainer Home Screen + Client Profile + Session History

This is one navigation flow, not three separate features. It is the structural shell of the entire app — the place every trainer lands when they open SuperTrainer and the hub through which they access everything about every client.

---

#### Onboarding — First Time Ever Opening the App

The very first time a trainer opens SuperTrainer, they go through a short onboarding flow before reaching the home screen. Two steps, nothing more:

**Step 1 — Trainer profile setup:**
Basic information about the trainer. Name, maybe a photo. Keep it minimal — do not ask for information that isn't immediately necessary. The goal of onboarding is to get out of the way as fast as possible.

**Step 2 — First client creation:**
Guided, friendly, low friction. Something like "Now let's add your first client." Trainer enters the client's name and basic details. This gets them to their first real interaction with the product immediately. The onboarding is not the product — the session is the product. Get them there fast.

After these two steps, trainer lands on the home screen and the real product begins.

---

#### The Home Screen

The home screen is a calendar-style view of today's sessions. It is the first thing a trainer sees every time they open the app after onboarding.

**When there are sessions today:**
A clean list of all sessions scheduled for today, showing session time and client name. Each row has two entry points:
- Tap the row → opens the full client profile
- "Today's Plan" button on the row → opens directly into that client's plan for today, skipping the full profile

This is the morning preparation view — the trainer scans their day, taps into clients they want to prepare for, checks or updates plans.

**When there are no sessions today:**
A simple, honest empty state. Something light — "No sessions today" or similar. No fake busyness, no forced content. The trainer is not opening this app for entertainment. If there's nothing today, say so clearly and let them navigate to whatever they actually need.

**Important reality check:** This app is not Instagram. Trainers will not open it for no reason. They open it because they need something — to prepare for a session, to check on a client, to ask the brain something. The home screen's job is to surface today's work clearly when it exists, and stay out of the way when it doesn't.

**Accessing past days:**
The app always allows the trainer to look back at previous days and past sessions. Just because today is empty doesn't mean the history is inaccessible. Navigation to client profiles and session history is always available through the Clients tab.

---

#### The Clients Screen (Bottom Nav Tab)

A full list of all the trainer's clients. Separate from the home screen — the home screen shows today's schedule, the clients screen shows everyone.

**What it looks like:**
- Clean alphabetical list by default
- Each row: client name and photo (optional)
- Search bar at the top — essential when a trainer has 25+ clients
- One sort option: "Date Added" — shows newest clients first

No complex grouping, no multiple filter options. Simple is right here. The trainer knows their clients — they just need to find them quickly.

---

#### The Client Profile

Tapping any client opens their full profile. This is the hub for everything about that person. Think of it like a player dashboard in FIFA — everything about this athlete in one place, at a glance.

**The overall status indicator:**
At the top of every client profile is a single holistic score or visual indicator — green, yellow, or red — that tells the trainer at a glance how this client is doing overall. Not just injury risk, not just progress — a combined signal.

What feeds into it:
- **Progression toward goals** — are they getting stronger, fitter, closer to what they came here for?
- **Injury risk** — pain frequency, severity, trend direction across sessions
- **Consistency** — are they showing up regularly or dropping off?

This is the "client score" — analogous to a Whoop recovery score but for coaching. A trainer should be able to open a client profile and know in one second whether this person needs attention or is doing well.

**Data maturity applies here too:** For new clients with fewer than 4-6 sessions, the indicator shows "Not enough data yet" rather than a misleading green. It becomes meaningful as sessions accumulate. The product never pretends to know more than it does.

**The full client profile contains:**

*Identity and Goals:*
- Name, photo, age, contact information
- Training goals (what they came here for — lose weight, build strength, rehab, performance)
- Training start date (how long they've been working with this trainer)
- Injury history (manually entered during onboarding or added over time)

*Current Status:*
- Overall status indicator (green/yellow/red score described above)
- Next scheduled session — date and time
- Today's plan if a session is imminent (hidden if no session is coming up soon)
- Current injury risk level (feeds into the overall score)

*Session History:*
- Chronological list of all sessions, most recent first
- Each session row shows: date, one-line AI summary of what was trained, any flags from that session
- Tap into any session to see full detail

**What is NOT on the client profile in V1:**
- Progress charts and trends (Tier 3 — needs real longitudinal data)
- Health documents — blood reports, body composition scans, medical notes (Tier 4)
- Wearable / recovery data (Tier 4)

These are all noted as future additions. Architecture should make them addable without restructuring the profile.

---

#### The Flag System

Flags are color-coded markers attached to sessions or specific observations within sessions. They exist so the trainer can scan past sessions and immediately identify which ones had significant moments without reading every entry.

**The four flag levels:**
- **Green** — positive observation (PR hit, form improvement, great energy)
- **Yellow** — minor concern (mild discomfort mentioned, slight form degradation)
- **Orange** — recurring concern (same issue appearing across multiple sessions)
- **Red** — significant concern (sharp pain, clear injury risk indicator)

**How flags are assigned:**
The AI assigns flags automatically based on what was logged in the session. If the trainer said "Pranav complained of sharp knee pain," the AI flags it red. If they said "slight forward lean on last rep," yellow. The AI reads the content and assigns the appropriate level.

**Trainer override — always:**
The trainer can change any flag at any time. Upgrade a yellow to a red if they realize in retrospect something was more significant than it seemed. Downgrade a red if they know context the AI doesn't. Add a flag the AI missed entirely. The AI assigns, the trainer always has final say.

**Where flags appear:**
- On the session row in the client's session history list — colored indicator so the trainer can scan without opening
- Inside the session detail — on the specific exercise card or observation card that triggered it
- On the client row on the home screen — a small indicator if there is a recent red or orange flag worth the trainer's attention

---

#### The Session Detail View

Tapping into any past session opens the full session detail screen.

**What it contains:**

*AI summary at the top:*
A single sentence or two summarizing what the session was about. "Upper body push day. Pranav hit a PR on bench press, complained of right shoulder tightness on the last set." This answers the quick question — "what did we do that day?" — in two seconds without scrolling.

This matters because trainers look back at sessions for two different reasons:
1. Quick check — "did we do legs or upper body last time?" — answered by the summary
2. Detailed reference — "exactly how much did he squat three weeks ago?" — answered by the full timeline below

*Full session timeline:*
The complete chronological record — exercise cards, observation cards, flags — in the exact order they happened. Same format as the live session screen. Every set, every rep, every observation, every note.

**Navigating between sessions:**
From inside a session detail, the trainer can swipe to the previous or next session for that client. They should never have to navigate back to the client profile and tap in again just to see an adjacent session. Less friction always — if they want to compare the last three leg sessions, three swipes, not six taps.

---

#### What Is NOT in Feature 4

To be explicit about scope:
- Billing, subscription management — Tier 4
- Multi-trainer / gym support — Tier 4
- Progress charts — Tier 3
- Injury risk scoring algorithm — Tier 3
- Health documents — Tier 4
- Wearable data on client profile — Tier 4

All of these are noted as known future additions. None of them block the core value of this feature.

### Feature 5: Calendar Integration

Connect Google Calendar or Apple Calendar via OAuth. Sessions already in the trainer's calendar automatically appear in the app.

When a session is detected from calendar:
- Session record created linked to the correct client (trainer maps calendar contacts to app clients once — automatic thereafter)
- Session pre-populated with scheduled time
- SuperTrainer's briefing notification triggered 10-15 minutes before the session start time (see Feature 2 for full briefing design)

Trainers can also create sessions manually inside the app. Both paths lead to the same session experience.

**Important distinction — two separate notifications:**

1. **Calendar reminder** — the trainer's own calendar app reminder (30 minutes before, 15 minutes, whatever they've set). SuperTrainer does not control this. It simply reads from the calendar to know when sessions are scheduled.

2. **SuperTrainer briefing notification** — fired by SuperTrainer 10-15 minutes before the session. This is the pre-session briefing we designed in Feature 2. It surfaces the four-layer briefing and opens the brain when tapped. This is the notification SuperTrainer owns and controls. The calendar integration provides the session time that SuperTrainer uses to schedule this notification at the right moment.

---

## Technical Architecture

See `TECH_STACK.md` for full analysis with alternatives and rationale for each choice.

**Summary:**
- **Mobile:** React Native + Expo (TypeScript)
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL on Railway
- **Task Queue:** ARQ + Redis on Railway
- **Auth:** Supabase Auth (free tier)
- **File Storage:** Supabase Storage (free tier)
- **STT:** Deepgram Nova-3 (keyterm prompting for gym vocabulary)
- **LLM:** Anthropic Claude Sonnet (tool_use for structured extraction; RAG for conversational agent)
- **Hosting:** Railway ($5-20/month)

### Data Model

**trainers** — id, email, password_hash, name, phone, tier, created_at, last_login

**clients** — id, trainer_id, name, email, phone, birth_date, training_start_date, goals[], injury_history, archived, created_at

**sessions** — id, trainer_id, client_id, started_at, ended_at, duration_minutes, audio_url, audio_duration_seconds, raw_transcript, processing_status, trainer_edited, plan_id (FK → session_plans, nullable — links session to the plan that was set for it, enabling plan vs. actual comparison), created_at, updated_at

**session_entries** — id, session_id, client_id, entry_type (exercise_card | observation_card), sequence_order, exercise_name, exercise_canonical, sets (JSONB), total_volume_kg, form_notes[], cues_given[], cue_effectiveness (JSONB), observation_text, attached_to_set, flag_color, flag_reason, performed_at, created_at
*(Note: This table replaces the original exercise_logs table to support both exercise cards and observation cards as a unified timeline)*

**injury_flags** — id, client_id, session_id, session_entry_id, body_part, pain_level (1-10), description, first_occurrence, last_occurrence, occurrence_count, resolved, resolved_at, flagged_at

**client_analysis** — id, client_id, total_sessions, last_session_date, avg_weight_increase_pct_per_week, current_volume_trend, injury_risk_score, injury_risk_level, risk_factors[], form_degradation_detected, overtraining_indicators, pain_pattern_detected, client_score (0-100 holistic score combining progression, injury risk, and consistency — feeds the green/yellow/red indicator on client profile), client_score_breakdown (JSONB — stores individual component scores for explainability), last_computed_at

**brain_conversations** — id, trainer_id, title (auto-generated from first message), created_at, updated_at
*(Stores conversation thread metadata — mirrors Claude/ChatGPT conversation history structure)*

**brain_messages** — id, conversation_id, trainer_id, role (user | assistant), content, created_at
*(Stores individual messages within a brain conversation thread)*

**exercises** — id, canonical_name, aliases[], category, primary_muscles[], equipment[], difficulty, common_errors (JSONB), created_at

**session_plans** — id, client_id, trainer_id, plan_text, planned_for_date, created_at
*(Stores plans set by trainer for upcoming sessions — feeds Section 2 of pre-session context)*

### API Design

All endpoints under `/api/v1/`

Success: `{"data": ..., "meta": {...}}`
Error: `{"error": {"code": "...", "message": "..."}}`
Pagination: cursor-based `?cursor=...&limit=20`
Weights stored in kilograms internally. Display conversion based on user preference.

**New endpoints added for V3 features:**
- `POST /sessions/{id}/voice-clip` — upload single voice clip, returns parsed entry in real time
- `GET /clients/{id}/pre-session-context` — returns adaptive pre-session context based on data maturity
- `GET /clients/{id}/briefing` — returns the 5-minute pre-session briefing (four-layer structure)
- `POST /agent/query` — conversational agent query (single client or cross-client)
- `POST /agent/action` — conversational agent action execution (create plan, modify plan, etc.)
- `GET /agent/conversations` — list all brain conversation threads for trainer
- `GET /agent/conversations/{id}` — retrieve full message history for a conversation thread
- `POST /agent/conversations` — start a new brain conversation thread
- `GET /clients/{id}/plan` — retrieve current plan for a client
- `POST /clients/{id}/plan` — create or update plan for a client (used by both trainer UI and brain)
- `GET /clients/{id}/score` — retrieve client score and breakdown
- `GET /calendar/upcoming` — returns upcoming sessions from connected calendar
- `POST /calendar/connect` — OAuth connection to Google/Apple Calendar

---

## Build Plan

### Assumptions
- Pranav: 3-4 hours/day for review, decisions, testing, and steering
- Claude Code: unlimited hours, 4 parallel agents — can build while Pranav is unavailable
- The bottleneck is review quality, not coding speed
- Timeline is driven by "done right," not "done fast" — extend if needed
- Bootstrapped: minimize costs until revenue
- TDD: tests first, implement until they pass
- **Synthetic data first:** Build 5 fake clients with 10-15 sessions each, varied histories, pain mentions, progression patterns. All Tier 1 and 2 features developed and tested against synthetic data before real users.

---

### Phase 1: Backend Foundation + Voice Pipeline (Weeks 1-4)

**Week 1-2: Backend Foundation**
- Project setup: FastAPI + SQLAlchemy + PostgreSQL (Railway)
- All data models + Alembic migrations:
  - trainers, clients, sessions, session_entries, session_plans, injury_flags, client_analysis, exercises, brain_conversations, brain_messages
- Seed script: 5 synthetic clients, 10-15 sessions each, varied pain/progress/muscle group patterns
- Client CRUD endpoints (list, create, get, update, archive)
- Session CRUD endpoints (create, get, list by client, update)
- Session plan CRUD endpoints (create, get, update for a client)
- Full test suite for all endpoints
- Milestone: all CRUD tests pass, API serves seeded synthetic data

**Week 3-4: Voice Pipeline**
- Deepgram Nova-3 integration (per-clip audio → transcript, real-time)
- Claude parsing service (transcript + full session context → structured JSON via tool_use)
- Session state management: client maintains full session state, sends with each clip
- Intent classification: new exercise, additive, set-level note, exercise-level note, observation card
- Additive parsing: second clip that says "oh, 80 kilos I forgot" correctly updates previous entry
- Rule-based validation layer (exercise name normalization, weight unit handling, implicit set expansion)
- Exercise database seed (100 common exercises + aliases)
- Audio upload endpoint (Supabase Storage)
- Real-time voice clip endpoint: POST /sessions/{id}/voice-clip → parsed entry within 3 seconds
- Parser test suite: 15+ transcript samples covering all intent types
- Milestone: speak naturally into phone → get back correctly parsed exercise card or observation card at 85%+ accuracy

---

### Phase 2: Mobile App — Core Session Flow (Weeks 5-7)

**Week 5-6: Core Session Screen + Navigation Shell**
- React Native + Expo project setup
- Bottom navigation: Home, Clients, Brain, Session tabs
- Trainer home screen: calendar-style today's sessions list, two entry points per row (full profile / today's plan)
- Empty state for no sessions today
- Clients screen: alphabetical list, search bar, date-added sort option
- Client profile screen: status indicator placeholder, identity/goals section, next session, session history list
- Session screen with real-time timeline (exercise cards + observation cards building live as trainer speaks)
- Tap-to-speak button: expands when active, contracts when stopped, haptic on both taps
- Inline editing on all timeline fields
- End session flow: review summary → "Anything to note for next time?" prompt → confirm → save
- API client layer with error handling
- Milestone: full navigation shell working, tap to record → see live timeline → save session

**Week 7: Session Detail + Client Profile Polish**
- Session detail view: AI one-line summary at top, full timeline below
- Swipe navigation between sessions (previous/next for same client)
- Flag display on session rows and inside session detail
- AI flag assignment on session save (green/yellow/orange/red based on content)
- Trainer flag override (tap any flag to change it)
- Client profile: session history list with flags visible on each row
- Onboarding flow: trainer profile setup → guided first client creation
- Milestone: complete client profile and session history working end to end

---

### Phase 3: Pre-Session Context + The Brain (Weeks 8-12)

**Week 8-9: Pre-Session Context — Deep Preparation View**
- Planning flow: voice input → AI structures into exercise cards (same format as session)
- Plan creation and modification endpoints
- Deep preparation view: today's plan displayed in structured exercise card format
- Plan fields are only what trainer said — weight/reps optional, never approximated, never inferred
- End-session plan dictation: "Anything to note for next time?" prompt saves to session_plans
- Plan vs. actual deviation tracked via plan_id FK on sessions table
- Tests for all planning flow behavior
- Milestone: trainer can voice-dictate a plan, see it structured, modify it — completely independent of sessions

**Week 10: Pre-Session Context — 5-Minute Briefing**
- Pre-session briefing service: four-layer generation (plan, last session, last same muscle-group session, exercise-specific trend flags)
- Data maturity gates enforced in backend (0/1/2-3/4+/10+ session thresholds)
- Briefing scoring logic: recency × severity × trend direction × actionability
- Briefing endpoint: GET /clients/{id}/briefing
- Push notification 10-15 minutes before scheduled session (Expo push) — not 5 minutes
- Notification content: client name + one-line preview of most important flag
- Briefing screen in mobile app: four layers, conditional display, no filler text
- "No plan set — want to add one?" nudge when plan is missing
- Tests for all data maturity gate behavior and briefing content accuracy
- Milestone: push notification fires, tap opens briefing, four layers display correctly based on data available

**Week 11-12: The Brain — Conversational Agent**
- RAG architecture: PostgreSQL semantic search, retrieve relevant session data per query
- Brain service: Claude Sonnet with system prompt enforcing three honest states
- Single-client query support with session citation
- Cross-client query support (retrieve from all clients, reason across)
- Three honest states enforced in prompting: full answer / partial answer / look it up
- Web search fallback for State 3 queries
- Action-taking V1: create plan, modify plan (add/remove exercise, update sets/reps/weight) via structured tool calls
- Confirmation required before any irreversible action
- Brain conversation history: threads stored in brain_conversations + brain_messages tables
- Brain tab in bottom nav: current conversation + conversation history (like Claude.ai)
- Brain accessible mid-session (secondary button on session screen, session state preserved)
- Brain opens from briefing notification with briefing context pre-loaded
- Full unrestricted brain — not scoped to single client even when opened from briefing
- Response time: under 3 seconds single-client, under 5 seconds cross-client
- Comprehensive tests: no hallucination on synthetic data, correct state identification per query type
- Milestone: ask brain anything about any client → accurate, cited, grounded answer. Brain creates and modifies plans on voice instruction.

---

### Phase 4: Calendar + Auth + Launch Prep (Weeks 13-16)

**Week 13: Calendar Integration**
- Google Calendar OAuth integration
- Apple Calendar integration
- Session auto-detection from calendar events
- Trainer-to-client contact mapping (one-time setup, automatic thereafter)
- Pre-session notification triggered from calendar events
- Calendar connection settings screen

**Week 14: Auth + Security**
- Supabase Auth integration (email signup + Google OAuth)
- JWT handling in mobile app (secure storage)
- Trainer-scoped data access (trainer can only see their clients)
- Password reset flow
- Audit logging

**Week 15: Settings + Polish**
- Settings screen (units kg/lbs, notifications, account, calendar connection)
- Loading states, error handling, edge cases throughout entire app
- Performance optimization (query efficiency, caching hot data)
- App Store / Play Store build prep (Expo EAS)
- Exercise database expanded to 200+ exercises

**Week 16: Beta Prep + Launch**
- Bug bash: fix everything found in self-testing
- Parser accuracy review: run full test suite, iterate prompt if needed
- Brain accuracy review: test all three honest states on real queries
- Deploy to production
- Onboard 5-10 beta trainers (personal network, gym contacts)
- Monitor: error rates, API costs, edit rate, brain query accuracy, plan adoption rate

---

### Phase 5: Intelligence Layer — Client Score + Patterns + Risk (Weeks 17-20)

**Week 17-18: Client Score + Pattern Detection**
- Client score algorithm: combines progression toward goals, injury risk, consistency
- Score stored in client_analysis.client_score with JSONB breakdown for explainability
- Green/yellow/red indicator populated on client profile
- Data maturity: "Not enough data yet" for clients with fewer than 4-6 sessions
- Rule-based pattern detection engine:
  - Weight progression rate (too fast / stagnant / healthy)
  - Pain frequency by body part (recurring = flag, threshold-based)
  - Form quality degradation (increasing error rate over sessions)
  - Volume and overtraining indicators
  - Cue effectiveness tracking
- client_analysis table recomputed after each session save
- Pattern results surfaced in briefing Layer 3 (trend flags for today's exercises)

**Week 19-20: Injury Risk Scoring + Progress Charts**
- Injury risk scoring (rule-based weighted formula, score 0-100, Low/Medium/High)
- Explainable: shows top risk factors driving the score
- Risk score feeds into overall client score
- Progress charts: weight progression per exercise, volume trends, pain frequency timeline, risk score history
- Charts accessible from client profile (Tier 3 section)
- Charts exportable

---

### Phase 6: Growth Features (Weeks 21-24+)

**Week 21-22: Client App + Wearables**
- Client-facing app (separate user role)
- Client sees own session history, goal progress, trainer-shared notes
- Whoop OAuth integration
- Oura OAuth integration
- Apple Health integration
- Recovery/HRV data surfaced in briefing as Layer 4 (same-day only, never estimated)

**Week 23-24: Multi-Trainer + Session Sharing + Scale**
- Multi-trainer support for gyms
- Permission-based client access
- Gym owner dashboard
- Session sharing: send session summary to client via email/SMS
- Performance at 100+ trainers
- Client Health Profile (Tier 4): upload blood reports, body composition scans, medical notes — brain can reason over all of it
- Stripe billing when appropriate
- Offline support (record offline, queue for upload, local cache, background sync)

---

## Build Philosophy

- **TDD:** Tests first. Build until they pass.
- **Synthetic data for development:** 5 fake clients with 10-15 sessions each, varied histories, pain mentions, progression patterns. All Tier 1 and 2 features developed against this data. Real users come after core features work well.
- **AI confidence calibration:** Every AI output reviewed for whether it claims more than data supports. When in doubt, say less.
- **Edit rate as health metric:** Track percentage of sessions requiring trainer editing after AI parsing. Target under 20%. Above 30% means parsing pipeline needs work before adding features.
- **The product earns trust:** Every interaction where the AI is wrong or overconfident costs trust that is hard to rebuild. Accuracy over impressiveness.
- **Data maturity is enforced, not suggested:** The backend enforces session count thresholds for all adaptive features. The AI never pretends to know more than it does.

---

## Success Metrics

**Phase 1 complete (Week 4):**
- Voice clip → structured session entry at 85%+ accuracy on test transcripts
- All intent types working: new exercise, additive, set-level note, observation card
- Full test suite passing on all CRUD endpoints

**Phase 2 complete (Week 7):**
- Full navigation shell working end to end
- Session recording → live timeline → save → session detail all working
- Swipe between sessions working
- Flag system working (AI assigns, trainer overrides)
- Onboarding complete

**Phase 3 complete (Week 12):**
- Planning flow working: voice dictate a plan → structured exercise cards → modify via brain
- Briefing working: four layers, correct data maturity gating, push notification fires 10-15 minutes before session
- Brain answering questions accurately with no hallucination on synthetic data
- Brain correctly identifying and communicating all three honest states
- Brain creating and modifying plans via voice instruction
- Conversation history working (thread-based, like Claude.ai)
- Brain accessible from anywhere in app, mid-session mode working
- App feels genuinely impressive — ready to show to a real trainer

**Beta launch (Week 16):**
- 5-10 trainers using the app
- Trainers recording 3+ sessions/week
- Parser accuracy 85%+ on real gym audio
- Under 20% of sessions require manual editing
- Brain query accuracy: no documented hallucination incidents
- Planning workflow adopted: trainers using voice-to-plan at least weekly
- Calendar integration working for majority of beta users

**Project success (portfolio horizon):**
- 5-10 real trainers say it meaningfully helped them
- Zero documented cases of AI hallucination causing a trainer to act on incorrect information
- Trainers using the planning workflow as a replacement for their previous notes/prep system
- Brain demonstrably useful on real data — trainers asking it questions they couldn't answer before

**Product-market fit (if it grows beyond the project):**
- 50+ trainers using regularly
- Trainers saying "I can't go back to how I did it before"
- Edit rate under 20%
- NPS > 40
- Brain action-taking expanded beyond plans — trainers managing sessions, clients, and schedules entirely through voice

---

## Open Risks

1. **Gym noise kills STT accuracy** — Test early with real gym recordings. If under 80% accuracy, investigate lapel mics or post-session recording workflow (trainer records summary after session ends).

2. **Trainers won't speak naturally into a phone mid-session** — The tap-to-speak model reduces friction, but there is still a behavioral change required. Mitigate by making the first 2-3 sessions feel immediately valuable — accurate structured data appearing in real time is the hook.

3. **Claude parsing degrades on edge cases** — Continuous prompt iteration required. Parser test suite is a living document. Every new edge case found in the wild gets added. Session state management across clips is the hardest technical problem here.

4. **AI overconfidence erodes trust** — The biggest risk to the product. One confident wrong answer from the conversational agent can kill a trainer's trust in the whole product. Data maturity gates and conservative prompting are primary mitigations.

5. **Session state management complexity** — Maintaining accurate context across 10-20 voice clips per session (which exercise is active, which set we're on) is technically tricky. If the AI loses track, attachment of notes to wrong exercises/sets. Needs careful testing with realistic multi-exercise sessions before any real users.

6. **Trainers won't record consistently** — The product only works with data. If adoption is under 3 sessions/week, intelligence layer is useless. Mitigate with push notifications, showing clear value from recordings immediately.

7. **Solo builder bottleneck** — Building the product solo is achievable. Sales, support, marketing, and engineering simultaneously is not. Plan to hire or find a co-founder if the product grows beyond the project phase.

8. **Brain action-taking reliability** — When the brain takes actions (modifying plans, archiving clients), errors have real consequences. Confirmation prompts for irreversible actions are mandatory. Test extensively before expanding action scope beyond V1. A wrong action taken by the brain is more damaging than a wrong answer — wrong answers can be corrected, wrong actions may have already affected data.
