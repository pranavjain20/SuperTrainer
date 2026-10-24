# SuperTrainer: Product Requirements

This describes SuperTrainer as it is now. It replaces a much longer planning document from February 2026, which covered features I haven't built and some I've since dropped (see [DECISIONS.md](DECISIONS.md)).

## The problem

A personal trainer at a gym works with twenty to forty clients, and every session produces details that matter later: the weights, which side is weaker, a twinge in someone's knee, a cue that fixed their form. Most of it never gets written down, because the trainer is busy coaching, and writing mid-session means looking away from the client. The details that do get written down end up in a notebook or the Notes app, where they're hard to find a week later.

So trainers walk into sessions without the full picture. They forget that a client mentioned knee pain last Tuesday, or miss that it keeps coming back after heavy squat weeks. Rafael Nadal's coach has one client and remembers everything. A gym trainer can't, and that's a limit of memory, not of care or knowledge.

## Who it's for

- **First:** independent and gym personal trainers with a full client list, who coach in person and already know their craft.
- **Not for:** people training themselves with an app, or anyone looking for an AI that writes programs or replaces the trainer's judgment.

## Goals

1. **Logging takes no attention away from the client.** The trainer talks the way they normally would, and each clip becomes structured cards within seconds.
2. **Talking naturally works.** Corrections fix earlier entries, notes attach to the exercise they're about, and an unclear clip leads to a question, not a guess.
3. **Every session leaves a short summary** that a trainer can read in a few seconds before the next session.
4. **Any question about a client gets an answer from their history,** across every session the trainer has logged.
5. **Never claim more than the data supports.** No invented causes, advice or trends, and a plain "the data doesn't say" when it doesn't.

## Non-goals

- Writing workout programs or telling the trainer what to do.
- Diagnosing injuries or giving medical advice.
- A client-facing app. The trainer is the only user.
- Accounts, billing, or hosting for real trainers yet. It runs locally for one trainer.

## The experience

**Clients.** The home tab shows today's sessions, and the clients tab lists every client. Each client's page shows their goals, injury history, plans and past sessions, with each session shown as one line per exercise, the way trainers write it in a notebook ("Goblet Squat: 16kg x10, 16kg x10, 16kg x10").

**A session.** The trainer starts a session and taps the mic between sets. Each clip turns into an exercise card (exercise, sets, reps, weight, RPE) or a note card (pain, form, anything else). Cards can be edited by hand. Saying "actually, that was thirty kilos" fixes the last card instead of adding a new one.

**The summary.** When the session ends, the trainer sees what the client did, a workout label (upper body, lower body, full body and so on) and a short AI summary. Editing the session later writes a fresh summary.

**Plans.** The trainer can dictate the next session's plan, and it's saved on the client's page.

**The Brain.** A chat tab where the trainer asks about clients in their own words, with a few suggested questions to start from.

**The demo.** The same app runs in a browser at [supertrainer-demo.vercel.app](https://supertrainer-demo.vercel.app), with recorded voice clips standing in for the mic and recorded answers standing in for the AI.

## How I'd know it works

**Already checked**

- A trainer who has been coaching for 15 years talked me through how they log sessions, and their real phrasing became test cases for the parser.
- Every summary and Brain answer in the demo was checked line by line against the session data it came from. The first pass found something wrong in 31 of the 69, like calling a set a personal best with nothing to compare it to. After fixing the prompts and how the data is written out for Claude, two real errors remain, both about the timeline of one client's hip.

**Not yet shown**

- **That trainers use it day to day.** It hasn't been used across weeks of real sessions with real clients.
- **That it's fast enough mid-session.** Each clip takes a few seconds to process. That's fine for one trainer between sets, but I haven't watched someone use it through a full session at the gym.
- **That the Brain stays accurate with months of history.** Today it reads all of a trainer's sessions at once, which works for the demo's five clients but won't scale to a full client list over a year.

## What I deliberately didn't build

- **AI-generated workout plans.** The trainer writes the plan. SuperTrainer remembers it.
- **Predictions from thin data.** No injury risk scores or trend claims until there's enough history to support them.
- **A live demo with a real mic and backend.** The demo replays real output instead, so it costs nothing to keep online and no visitor's voice or data goes anywhere.
