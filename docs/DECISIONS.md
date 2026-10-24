# Key Decisions

The decisions that shaped SuperTrainer and are still true in the code today. Each one says what it was before, what it is now, and why I changed it. Most came from watching real training sessions or from holding the app on my phone and noticing what felt wrong. The commit messages hold the full before and after of each change.

A few terms used throughout:

- **Clip:** one short voice recording. The trainer taps to start, speaks, and taps to stop.
- **Transcript:** the text of a clip, produced by Deepgram, a speech-to-text service.
- **Parser:** the step where Claude reads a transcript and turns it into structured data (exercise, sets, reps, weight, notes).
- **Entry:** one item on a session's timeline. It is either an exercise card or an observation (a note about the client).
- **RPE:** rating of perceived exertion, the client's effort on a set from 1 to 10.
- **Cue:** a short coaching instruction the trainer gives, like "knees out".

---

## 1. Log by voice in short clips

**Before.** Trainers log on paper, and the trainer apps I looked at use forms: pick an exercise, then fill in sets, reps and weight. The other options I weighed were recording the whole session continuously, or having the trainer step into a logging screen between sets.

**After.** The recording screen has one large button. The trainer taps it, says what happened ("three sets of squats, 80 kilos, 10 reps"), and taps again. Each clip is sent off and comes back as structured cards a few seconds later.

**Why.** Trainers won't fill in forms between sets, and most of them still use a paper notebook because it's faster. Continuous recording would capture private conversation along with music and gym noise, and the trainer and client may not want the whole hour recorded. Tap to speak keeps the trainer in control of what gets captured and costs them a few seconds.

---

## 2. Process each clip right away, with the whole session as context

**Before.** The plan was to upload the session's audio in one batch at the end and parse it then.

**After.** Every clip is parsed as soon as it arrives. The parser is given every entry already logged in the session, each with a number, so it can choose between adding a new card and changing an existing one. "That last set was 30 kilos" corrects the earlier set instead of creating a second exercise. "Second set, 8 reps at 85" adds a set to the squats already logged. A change only overwrites data when the trainer clearly signals a correction ("no wait", "actually"); otherwise it adds.

**Why.** By the end of a session the trainer has forgotten the details, so mistakes have to show up while they can still fix them. Trainers also don't speak in tidy, complete records. They remember the weight a clip later, or correct themselves, and the parser can only handle that if it can see what came before.

---

## 3. Ask instead of guessing, and keep the question off the timeline

**Before.** When the parser couldn't make sense of a clip, it created a yellow observation card. On the phone that looked identical to a real note about the client, like "energy is low".

**After.** The parser is told that when it's in doubt between a dubious exercise card and asking, it should always ask. That covers noise ("hello testing"), unclear speech, and a reference that could mean two different exercises. These questions are never saved as entries. The app shows them as a separate system message that offers to re-record or type the entry instead.

**Why.** A wrong card that looks right is worse than a question, because the trainer won't notice it. And mid-session the trainer's attention is on the client, so a glance at the phone has to make it obvious whether something is about the client or the app needs help. The session timeline should only ever contain what the trainer said.

---

## 4. Notes attach to the set they're about, and only when the trainer says so

**Before.** The first data model stored a session as a list of exercises, so a note said between exercises had nowhere to go. Later, observations were floating notes with no link to an exercise, even though the database already had a field for the set number.

**After.** A session is a timeline of entries in the order they happened, mixing exercise cards and observations. Anything said during an exercise ("grip slipped", "lower back pain after rep 7 on set 3") is stored on that set. A comment said between exercises ("his lower back is hurting") stays a session-level note, and the parser adds what had been done so far ("energy dropping further after clamshells and squats").

**Why.** I went to a real session and paid attention to what was said. Pain, form and effort almost always belong to a specific set, and the set is what makes them useful later. The first prompt got the between-exercise case wrong: it saw "lower back pain" with deadlifts in the session and linked them. That's reasonable logic but wrong, because a trainer who meant the deadlifts would say "from those deadlifts". So the rule is that a note is linked to an exercise only when the trainer names it.

---

## 5. Show sets the way trainers write them

**Before.** Sets were shown in a table with a row per set and columns for reps, weight and RPE.

**After.** History shows each exercise as one short line, like "Squat: 80kg×8, 85kg×8, 90kg×6". A bodyweight exercise is "Pull-ups: 12, 10, 8" and a timed one is "Plank: 60s, 45s". The full table is still there for editing.

**Why.** A trainer with 15 years of experience found the table confusing on first look. They write "squat: 4x8, 5x8, 6x8" in his notes and reads that fluently. Before every exercise they glance back at what the client did last time, so this view has to be as quick to scan as a notebook page. I tried several more designed versions (coloured backgrounds, chips, split fonts) and plain text lines read best.

---

## 6. The session summary may only say what the data says

**Before.** Each past session showed only a workout label like "Full Body", which doesn't bring a session back to mind.

**After.** When a session ends, Claude writes a 2–3 sentence recap: what was done, how it went, and anything worth remembering. The prompt gives Claude each entry as one plain line and sets these rules:

- Never invent numbers, feelings, causes or advice.
- Don't judge effort ("worked hard") unless an RPE or a note says so.
- Call a weight a personal best only when that exercise has an earlier best in the data and the new weight beats it.
- A cue is labelled "timing not recorded", so the summary must never say something went wrong "despite" a cue. The parser stores a cue meant for next time the same way as one said mid-set.

It also runs at temperature 0, the setting that makes Claude give its most likely wording, so the same session gets the same recap.

**Why.** The trainer I tested with asked for exactly this kind of recap without being prompted. But a recap that invents a cause or a personal best is worse than none, because the trainer will trust it. Before writing the rules I fact-checked 69 recorded summaries and Brain answers against their session data, and 31 of them had something wrong. With the rules in place, the same check finds two real errors, both in Brain answers about the timeline of one client's hip. One error came from the data, not the wording. Older sets store their weight in a different field, and reading only the newer field told Claude those sets had no load.

---

## 7. Clear the summary whenever the session changes

**Before.** There was no stored summary, so nothing could go stale.

**After.** The summary is saved on the session after it's written, and adding, editing or deleting any entry clears it. The next request writes a fresh one, and an open screen refetches it.

**Why.** Trainers fix entries after the fact. A summary that still says 25 kilos after the weight was corrected to 30 would contradict the card right below it. Clearing it in the same place every entry change goes through means no edit path can forget to.

---

## 8. The Brain answers only from logged data, with every client listed first

**Before.** The Brain tab said "Coming in Phase 3".

**After.** The Brain is a chat where a trainer asks about their clients ("who has an injury I should plan around?"). Each question goes to Claude with all of that trainer's data: a roster of every client's goals and injury history, then each client's sessions in order, using the same entry lines as the summaries. Claude must answer only from that data, say so when the data doesn't cover the question, and never state a cause, trend or advice the data doesn't. Dates are given relative to today ("3 days ago"), and archived clients and other trainers' data are left out.

**Why.** Without the roster at the top, a question like "who has an injury?" skipped a client whose injury was only in her profile and never in a session note. Sending everything in one call fits a trainer's real amount of data today. Once histories outgrow a single prompt, the plan is to search them and send only the relevant pieces.

---

## 9. Decide the workout label in one place, on the backend

**Before.** The app labelled workouts two ways. The end-of-session screen asked the backend, which classifies by muscle group. History cards used a keyword match in the app. One session could read "Lower Body" on one screen and "Full Body" on another. Earlier, a naming mismatch ("goblet_squat" against "Goblet Squat") made every session read "Session".

**After.** Every session the backend returns carries its workout label, worked out from its exercises each time it's read. The keyword matcher in the app is deleted, and every screen shows the backend's label.

**Why.** Two pieces of code answering the same question will eventually disagree. Working the label out on each read also means it's right immediately after an edit, with nothing stored to go stale.

---

## 10. The web demo replays real recorded output

**Before.** Seeing the app needed a phone or simulator, a running backend, Deepgram and Claude.

**After.** The demo is a static website. A script runs the real pipeline once against seeded sample clients and records everything: six spoken sample clips through voice logging, including one that corrects an earlier set; a plan dictation; the summaries; and the Brain's answers to the suggested questions. In the demo the record button plays the next sample clip, and the app's requests are answered in the browser from those recordings, with the same waits the real runs took. Transcripts are kept exactly as Deepgram returned them, mistakes included ("Q knees out" for "cue knees out").

**Why.** A live demo would cost money on every visit, need API keys on a server, and send every visitor's voice to a server. A replay costs nothing to run and holds only made-up clients. Because every clip, summary and answer came from the real pipeline, the demo shows what the product actually does. The trade-off is that the demo can't parse anything new. Typed entries return an explanation instead, and editing an entry doesn't rewrite its summary in the demo the way it does in the app.
