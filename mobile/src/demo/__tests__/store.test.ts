import fixture from "../fixture.json";
import { freshen } from "../store";

const DAY_MS = 24 * 60 * 60 * 1000;

function localDay(iso: string): number {
  const d = new Date(iso);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

describe("freshen", () => {
  // Morning, afternoon and just after midnight: the cap on today's sessions
  // behaves differently in each
  const nows = [
    new Date(2027, 2, 10, 9, 5),
    new Date(2027, 2, 10, 20, 40),
    new Date(2027, 2, 10, 0, 20),
  ];

  it.each(nows)("puts the most recent seeded day on today (%s)", (now) => {
    const state = freshen(now);
    const latest = Math.max(...state.sessions.map((s) => localDay(s.started_at)));
    expect(latest).toBe(localDay(now.toISOString()));
  });

  it.each(nows.slice(0, 2))(
    "has every finished session today ending before now (%s)",
    (now) => {
      const state = freshen(now);
      for (const s of state.sessions) {
        if (s.ended_at)
          expect(new Date(s.ended_at).getTime()).toBeLessThanOrEqual(now.getTime());
      }
    },
  );

  it("keeps the gaps between sessions' days", () => {
    const state = freshen(nows[0]);
    const daysApart = (a: string, b: string) =>
      Math.round((localDay(a) - localDay(b)) / DAY_MS);
    const [first, second] = [...fixture.sessions].sort((a, b) =>
      b.started_at.localeCompare(a.started_at),
    );
    const [f, s] = [first, second].map((x) => state.sessions.find((y) => y.id === x.id)!);
    expect(daysApart(f.started_at, s.started_at)).toBe(
      daysApart(first.started_at, second.started_at),
    );
  });

  it("keeps each session's length and entries inside it", () => {
    const state = freshen(nows[1]);
    for (const s of state.sessions) {
      const original = fixture.sessions.find((x) => x.id === s.id)!;
      if (s.ended_at && original.ended_at) {
        const len = (a: string, b: string) =>
          new Date(b).getTime() - new Date(a).getTime();
        expect(len(s.started_at, s.ended_at)).toBe(
          len(original.started_at, original.ended_at),
        );
      }
    }
    for (const e of state.entries) {
      const session = state.sessions.find((s) => s.id === e.session_id)!;
      if (e.performed_at && session.ended_at) {
        expect(
          e.performed_at >= session.started_at && e.performed_at <= session.ended_at,
        ).toBe(true);
      }
    }
  });

  it("moves plan dates by whole days", () => {
    const state = freshen(nows[0]);
    const original = fixture.plans.find((p) => p.planned_for_date)!;
    const moved = state.plans.find((p) => p.id === original.id)!;
    const shift =
      (new Date(moved.planned_for_date!).getTime() -
        new Date(original.planned_for_date!).getTime()) /
      DAY_MS;
    expect(Number.isInteger(shift)).toBe(true);
  });

  it("starts with no clips replayed", () => {
    const state = freshen(nows[0]);
    expect(state.clipsUsed).toEqual({});
    expect(state.replayIds).toEqual({});
    expect(state.version).toBe(`${fixture.captured_at}|${nows[0].toDateString()}`);
  });

  const upcoming = (now: Date) =>
    freshen(now).sessions.filter((s) => s.id.startsWith("upcoming-"));

  it("schedules a session later today for each client who hasn't trained today", () => {
    const now = nows[0];
    const state = freshen(now);
    const trainedToday = new Set(
      state.sessions
        .filter((s) => !s.id.startsWith("upcoming-"))
        .filter((s) => localDay(s.started_at) === localDay(now.toISOString()))
        .map((s) => s.client_id),
    );
    const sessions = upcoming(now);
    expect(sessions.map((s) => s.client_id).sort()).toEqual(
      fixture.clients
        .map((c) => c.id)
        .filter((id) => !trainedToday.has(id))
        .sort(),
    );
    const times = sessions.map((s) => new Date(s.started_at).getTime());
    expect(times.every((t) => t > now.getTime())).toBe(true);
    expect([...times].sort((a, b) => a - b)).toEqual(times);
    for (const s of sessions) {
      expect(s.ended_at).toBeNull();
      expect(s.scheduled_for).toBe(s.started_at);
      expect(localDay(s.started_at)).toBe(localDay(now.toISOString()));
    }
  });

  it.each([
    new Date(2027, 2, 10, 20, 0),
    new Date(2027, 2, 10, 22, 50),
    new Date(2027, 2, 10, 23, 55),
  ])("keeps evening sessions after now and before midnight (%s)", (late) => {
    const times = upcoming(late).map((s) => new Date(s.started_at).getTime());
    expect(times.length).toBeGreaterThan(0);
    expect(times.every((t) => t > late.getTime())).toBe(true);
    expect(
      times.every(
        (t) => localDay(new Date(t).toISOString()) === localDay(late.toISOString()),
      ),
    ).toBe(true);
    expect(new Set(times).size).toBe(times.length);
  });

  it("has a recorded brief for every upcoming session's client", () => {
    for (const s of upcoming(nows[0])) {
      expect(
        (fixture.session_briefs as Record<string, { ai_brief: string | null }>)[
          s.client_id
        ]?.ai_brief,
      ).toBeTruthy();
    }
  });
});

describe("the saved copy", () => {
  type StoreModule = typeof import("../store");

  // A fresh module per test, as on a new page load
  function loadStore(storage: Partial<Storage>): StoreModule {
    (globalThis as { localStorage?: Partial<Storage> }).localStorage = storage;
    let store!: StoreModule;
    jest.isolateModules(() => {
      store = require("../store");
    });
    return store;
  }

  function memoryStorage(): Partial<Storage> {
    const items = new Map<string, string>();
    return {
      getItem: (k) => items.get(k) ?? null,
      setItem: (k, v) => void items.set(k, v),
    };
  }

  afterEach(() => {
    delete (globalThis as { localStorage?: unknown }).localStorage;
  });

  it("comes back on the next visit", () => {
    const storage = memoryStorage();
    const first = loadStore(storage);
    first.getState().clients[0].name = "Renamed";
    first.save();
    expect(loadStore(storage).getState().clients[0].name).toBe("Renamed");
  });

  it("is replaced when the fixture is re-recorded", () => {
    const storage = memoryStorage();
    storage.setItem!(
      "supertrainer-demo",
      JSON.stringify({ version: "older recording", clients: [] }),
    );
    expect(loadStore(storage).getState().clients).toHaveLength(fixture.clients.length);
  });

  it("is replaced on a new day, so today's schedule is current", () => {
    const storage = memoryStorage();
    storage.setItem!(
      "supertrainer-demo",
      JSON.stringify({ version: `${fixture.captured_at}|Mon Jan 01 2001`, clients: [] }),
    );
    expect(loadStore(storage).getState().clients).toHaveLength(fixture.clients.length);
  });

  it("falls back to memory when storage throws", () => {
    const store = loadStore({
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    });
    expect(store.getState().clients).toHaveLength(fixture.clients.length);
    expect(() => store.save()).not.toThrow();
  });

  it("resets to the recorded data", () => {
    const store = loadStore(memoryStorage());
    store.getState().sessions = [];
    store.resetDemo();
    const recorded = store
      .getState()
      .sessions.filter((s) => !s.id.startsWith("upcoming-"));
    expect(recorded).toHaveLength(fixture.sessions.length);
  });
});
