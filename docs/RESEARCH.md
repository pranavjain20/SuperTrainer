# SuperTrainer — Research

**Last checked:** October 24, 2026

This document says what published research SuperTrainer rests on, and what it does not rest on. Research is cited for one thing only: showing that the problem SuperTrainer tackles is real. Everything SuperTrainer does about that problem (voice notes, session summaries, the Brain) is my own design. I was guided by what I read, but no study tested SuperTrainer or prescribes how it works.

## The problem, in one paragraph

A personal trainer works with many clients. Each client has a history: what they lifted last time, what hurt, what they said about their week, what the trainer promised to try next. Most of that lives in the trainer's head or in scattered notes. Details get lost, small warning signs get missed, and the client feels less known. SuperTrainer is my attempt to give the trainer a reliable memory of every client.

## Terms used here

- **Observational study:** researchers look at what already happened, without assigning people to groups. It can show that two things go together, but not prove that one causes the other.
- **Matching:** a way to make an observational comparison fairer. Each person in one group is paired with a similar person in the other group, so the groups look alike before the comparison starts.
- **Time-loss injury:** an injury that makes an athlete miss training or competition. Many sports studies count only these.
- **Overuse problem:** pain or a problem that builds up gradually from repeated load, rather than from one accident.

---

## What the research says

### Claim 1: Information held only in memory is lost fast; written notes keep it

- **Bhabra et al. 2007 (Annals of the Royal College of Surgeons of England).** Junior doctors handed over 12 simulated patients to each other, one-to-one, five times in a row, using three methods. After five handovers, "only 2.5% of patient information was retained using the verbal-only handover method." With talk plus note-taking, 85.5% was retained, and with a printed handout of all patient information, 99%.
  - *What it shows:* when many people's details are carried by memory and talk alone, almost nothing survives. Writing things down changes that dramatically.
  - *What it does not show:* this was a simulated hospital exercise, and the information passed between several people rather than staying with one person. It says nothing about trainers. The authors themselves note it "is an artificial scenario." I use it as evidence for the general point (memory alone is unreliable for many people's details), not as a measure of how much a trainer forgets.

I looked for a solid source on how many clients a typical trainer carries. I only found vendor and course-provider blogs quoting "15 to 25 clients", with no stated method, so I do not cite a number.

### Claim 2: People still want a human trainer

- **Les Mills 2026 Global Fitness Report.** A survey of more than 10,000 consumers across five continents. In the published summary, "only 10% of respondents favored an AI coach," while 52% either "strongly preferring" (31%) or "leaning toward" (21%) a human trainer, and 37% were undecided. Younger people were not much different: "Just 11% of 16-27 year-olds and 9% of 28-40 year-olds prefer AI-generated content."
  - *What it shows:* in a large survey, very few people say they would pick an AI coach over a human one.
  - *What it does not show:* this is a company survey, not peer-reviewed, and Les Mills sells instructor-led classes, so it has an interest in the answer. The public pages do not describe the method or the survey dates. It measures stated preference, not what people actually do.

### Claim 3: Human coaching on top of AI did better than AI alone

- **Kapoor, Narayanan & Manchanda (Marketing Science, published 2026).** About 65,000 users of HealthifyMe, a weight-loss app in India with two paid plans: AI coaching only, and AI coaching plus access to human coaches. Each human-plan user was matched with a similar AI-only user. Stanford's write-up reports that the human-plus-AI group "lost an average of about 5 pounds over three months," while the AI-only group "lost a little less than 3 pounds on average," "with the weight loss being over 74% higher for consumers with AI plus human coaches." The journal's press release adds that users with human coaches logged food about twice as often (102.0 vs 49.7 times a week) and that the gain "appears to operate through more ambitious goals and much more consistent tracking."
  - *What it shows:* adding a human coach to an AI app went along with more weight loss and more consistent tracking, after a careful attempt to compare like with like.
  - *What it does not show:* it is observational, so matching reduces but cannot remove the chance that more motivated people chose the human plan. "74% more" is relative; the actual gap is about 2 pounds over three months. The human coaches were remote nutrition coaches inside an app, not in-person trainers. And the AI coached the users directly. SuperTrainer does something different (the AI helps the trainer, not the client), so this study does not test SuperTrainer's setup.

### Claim 4: Many pain problems never show up as a missed session

- **Clarsen, Myklebust & Bahr 2013 (British Journal of Sports Medicine).** 313 athletes from five sports answered a short questionnaire every week for 13 weeks about problems in the knee, lower back and shoulder. The weekly questionnaire recorded 419 overuse problems, and "Each week, an average of 39% of athletes reported having overuse problems." Standard injury recording, which mostly counts time-loss injuries, "registered only 40 overuse injuries" in the same body areas. The authors conclude that standard methods "only capture a small percentage of the overuse problems affecting the athletes, largely because few problems led to time loss."
  - *What it shows:* regularly asking about pain and recording it catches far more problems than waiting until someone has to stop training.
  - *What it does not show:* these were competitive athletes, not gym clients. The study does not show that recording pain prevents injuries, or that any pattern in the records predicts a future injury.

---

## My design choices

Everything below is my own choice. No study above tested any of it, and none of it should be described as proven.

- **Voice notes instead of typing.** Trainers speak short notes during or after a session, and SuperTrainer turns them into a structured session log (exercises, sets, weights, pain, comments). I chose voice because a trainer's hands and attention are on the client. Claim 1 says notes matter; it does not say voice notes are as good as written ones.
- **Pain stands out, every session.** A note about pain is flagged red on the session timeline, and each client's injury history goes to the Brain with every question, so a small complaint isn't lost just because it never stopped a session. This is inspired by Claim 4, but I have not tested whether it helps trainers catch problems earlier.
- **Summaries that don't claim more than the data.** After each session the app writes a short recap from that session's log, including anything worth remembering next time (pain, a form breakdown, a cue given). It is told never to invent numbers, feelings, causes or advice, and not to judge effort unless a note says so.
- **The Brain answers only from logged data.** The chat assistant answers questions about clients using only the sessions the trainer has logged and each client's profile. If the data doesn't say, it says so, and it never states a cause, plan, trend or advice the data doesn't state.
- **The trainer stays in charge.** SuperTrainer prepares and remembers; the trainer decides. This follows from Claims 2 and 3 (people want a human, and the human seemed to add value), but the specific split of work is mine.

---

## Open questions

- Do trainers actually log more, and more accurately, by voice than by typing? I have not measured it.
- Does a better memory of each client change anything clients care about (results, staying with the trainer)? No study above answers this for SuperTrainer.
- How often do the summaries or the Brain get something wrong, and does the trainer notice? This needs testing with real sessions.

---

## References

- Bhabra G, Mackeith S, Monteiro P, Pothier DD (2007). An experimental comparison of handover methods. *Annals of the Royal College of Surgeons of England* 89(3):298-300. https://doi.org/10.1308/003588407X168352
- Les Mills (2026). 2026 Global Fitness Report, press release via Fitt Insider: https://insider.fitt.co/press-release/fitness-fans-shunning-ai-in-favor-of-human-connection-finds-les-mills-2026-global-fitness-report/ and Les Mills summary: https://www.lesmills.com/articles/we-want-humans-not-algorithms
- Kapoor A, Narayanan S, Manchanda P (2026). Does Access to Human Coaches Lead to More Weight Loss Than With AI Coaches Alone? *Marketing Science*. https://doi.org/10.1287/mksc.2023.0029
  - Stanford GSB write-up: https://www.gsb.stanford.edu/insights/ai-can-coach-you-lose-weight-human-touch-still-helps
  - INFORMS press release: https://www.informs.org/News-Room/INFORMS-Releases/News-Releases/Research-Finds-that-AI-Weight-Loss-Apps-Work-Best-When-Combined-with-Human-Coaching
- Clarsen B, Myklebust G, Bahr R (2013). Development and validation of a new method for the registration of overuse injuries in sports injury epidemiology: the Oslo Sports Trauma Research Centre (OSTRC) overuse injury questionnaire. *British Journal of Sports Medicine* 47(8):495-502. https://doi.org/10.1136/bjsports-2012-091524
