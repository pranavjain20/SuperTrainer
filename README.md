# SuperTrainer

SuperTrainer gives a personal trainer the memory of a coach with one client. The trainer talks during a session, and each voice note becomes a log of what the client did. Before each session it gives the trainer AI notes on that client, after it writes a short summary, and the trainer can ask it anything about any client.

Try the demo in your browser: [supertrainer-demo.vercel.app](https://supertrainer-demo.vercel.app)

## The problem

I train with a personal trainer, and every session he gives me so many small cues: which side is working harder, when my lower back starts taking over, how a set actually felt. Almost none of it gets written down, because he's busy coaching, and by the next week it's gone.

Rafael Nadal's coach doesn't have this problem, because he has one client. A trainer at a gym has twenty to forty, and nobody can keep that much in their head. So they forget that a client mentioned knee pain last Tuesday, or miss that it keeps coming back after heavy squat weeks, until it turns into an injury. And the ones who do keep notes write them in a notebook or the Notes app, which means looking away from the client mid-session.

## How it works

During a session the trainer taps the mic and says what happened, the way they'd say it out loud: "Goblet squats, three sets of ten at sixteen kilos, the last set was an RPE of eight." Deepgram turns the clip into text, and Claude turns the text into an exercise card with the sets, reps and weights, or a note card for anything else, like pain or a form cue. Exercise names are matched to a fixed exercise list, so "goblet squats" and "goblet squat" end up as the same exercise in the client's history.

Each clip is read with the rest of the session in view, so the trainer can talk the way people actually talk. "Actually, that last set was thirty kilos" fixes the earlier card instead of adding a new one, and a comment about how a set went, like "grip slipped on the last rep", is saved on that set. When a clip is unclear, the app asks the trainer instead of guessing.

When the session ends, SuperTrainer writes a short summary of what the client did and anything worth watching next time. The summary only uses what was logged: it doesn't invent causes or advice, and it only calls something a personal best when there's an earlier best to compare against. If the trainer edits the session later, the summary is written again.

Every morning, the trainer's schedule shows the day's sessions, and each one has AI notes on that client: pain or flags from the past few weeks, lifts whose weight has moved, and muscle groups they haven't trained lately, like "Jake mentioned lower back tightness after squats 12 days ago, worth checking in before loading the bar" or "calves haven't been trained in four weeks, a set of calf raises would cover it". The weight changes and gaps are worked out in code from the logged sessions, so the notes only put them into words.

The Brain is a chat where the trainer can ask about their clients, like "anything I should watch out for with Elena today?" or "how is Jake's bench press progressing?". It answers from every session the trainer has logged, plus each client's goals and injury history, and when the data doesn't have the answer, it says so. Trainers can also dictate the plan for the next session, and the client's history shows each past session in one line per exercise, the way trainers write it in a notebook.

The backend is Python (FastAPI) on Postgres, and the app is React Native (Expo). The browser demo runs the same app with no server: everything it shows was recorded once from the real backend and is replayed, so it costs nothing to run and nothing you type leaves your browser.

## Running it

You need Docker, Python 3.12, Node 20 or newer, and API keys for Deepgram and Anthropic.

```bash
docker compose up -d                  # Postgres for the app (port 5434) and for tests (5433)

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # add DEEPGRAM_API_KEY and ANTHROPIC_API_KEY
alembic upgrade head
python -m app.seed                    # a trainer, five clients and their past sessions
uvicorn app.main:app --reload
pytest                                # backend tests, against the test database
```

```bash
cd mobile
npm ci
npx expo start                        # press i for the iOS simulator
npm test                              # app tests
```

The browser demo needs no backend or keys:

```bash
cd mobile
EXPO_PUBLIC_DEMO=1 npx expo start --web   # the demo, locally
npm run export:demo                       # build it into mobile/dist-demo
```

To record new demo data, run `python scripts/export_web_demo.py` from `backend/` against a freshly seeded local backend. It writes `mobile/src/demo/fixture.json` and the demo's audio clips.

More detail: [PRD](docs/PRD.md) · [Key decisions](docs/DECISIONS.md) · [How it works, technically](docs/HOW_IT_WORKS.md) · [Research](docs/RESEARCH.md)

## License

MIT. See [LICENSE](LICENSE).
