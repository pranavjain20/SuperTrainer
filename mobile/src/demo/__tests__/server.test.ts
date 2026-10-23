import fixture from "../fixture.json";
import { demoFetch, totalVolume } from "../server";
import { getState, resetDemo } from "../store";

// Replayed clips wait as long as the real pipeline took; fake timers skip that
async function call(method: string, path: string, body?: unknown) {
  const pending = demoFetch(`https://api.example/api/v1${path}`, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  await jest.runAllTimersAsync();
  const res = await pending;
  return { status: res.status, body: res.status === 204 ? null : await res.json() };
}

const sarah = fixture.clients.find((c) => c.name === "Sarah Chen")!;

async function startSession() {
  const res = await call("POST", "/sessions", {
    client_id: sarah.id,
    started_at: new Date().toISOString(),
  });
  return res.body.data.id as string;
}

const recordClip = (sessionId: string) =>
  call("POST", `/sessions/${sessionId}/voice-clip`);

beforeEach(() => {
  jest.useFakeTimers();
  resetDemo();
});

afterEach(() => jest.useRealTimers());

describe("clients", () => {
  it("lists non-archived clients newest first, paginated by cursor", async () => {
    const page1 = await call("GET", "/clients?limit=3");
    expect(page1.body.data).toHaveLength(3);
    expect(page1.body.meta).toEqual({
      cursor: page1.body.data[2].id,
      limit: 3,
      has_more: true,
    });

    const page2 = await call("GET", `/clients?limit=3&cursor=${page1.body.meta.cursor}`);
    expect(page2.body.meta.has_more).toBe(false);
    const ids = [...page1.body.data, ...page2.body.data].map((c: { id: string }) => c.id);
    expect(new Set(ids).size).toBe(fixture.clients.length);
  });

  it("hides archived clients unless asked", async () => {
    await call("PATCH", `/clients/${sarah.id}`, { archived: true });
    expect(
      (await call("GET", "/clients")).body.data.map((c: { id: string }) => c.id),
    ).not.toContain(sarah.id);
    expect(
      (await call("GET", "/clients?include_archived=true")).body.data.map(
        (c: { id: string }) => c.id,
      ),
    ).toContain(sarah.id);
  });

  it("skips null fields on PATCH, like the backend", async () => {
    const res = await call("PATCH", `/clients/${sarah.id}`, {
      email: null,
      phone: "+1-555-9999",
    });
    expect(res.body.data.email).toBe(sarah.email);
    expect(res.body.data.phone).toBe("+1-555-9999");
  });

  it("answers an unknown client with the backend's 404 envelope", async () => {
    const res = await call("GET", "/clients/nope");
    expect(res.status).toBe(404);
    expect(res.body).toEqual({
      error: { code: "http_404", message: "Client not found" },
    });
  });
});

describe("sessions", () => {
  it("filters the trainer's sessions to a date in the given timezone", async () => {
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/New_York",
    }).format(new Date());
    const res = await call(
      "GET",
      `/sessions?scheduled_for_date=${today}&tz=America/New_York`,
    );
    expect(res.body.data.length).toBeGreaterThan(0);
    for (const s of res.body.data) {
      expect(
        new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(
          new Date(s.started_at),
        ),
      ).toBe(today);
    }
  });

  it("creates a session with the backend's defaults", async () => {
    const id = await startSession();
    const { body } = await call("GET", `/sessions/${id}`);
    expect(body.data).toMatchObject({
      client_id: sarah.id,
      ended_at: null,
      processing_status: "pending",
      trainer_edited: false,
    });
  });

  it("rejects a plan that belongs to another client", async () => {
    const otherPlan = fixture.plans.find((p) => p.client_id !== sarah.id)!;
    const res = await call("POST", "/sessions", {
      client_id: sarah.id,
      started_at: new Date().toISOString(),
      plan_id: otherPlan.id,
    });
    expect(res.status).toBe(422);
  });

  it("computes duration when a session ends", async () => {
    const id = await startSession();
    const started = getState().sessions.find((s) => s.id === id)!.started_at;
    const ended = new Date(
      new Date(started).getTime() + 47 * 60_000 + 20_000,
    ).toISOString();
    const res = await call("PATCH", `/sessions/${id}`, { ended_at: ended });
    expect(res.body.data.duration_minutes).toBe(47);
  });

  it("deletes a session's entries with it", async () => {
    const id = await startSession();
    await recordClip(id);
    expect((await call("DELETE", `/sessions/${id}`)).status).toBe(204);
    expect(getState().entries.filter((e) => e.session_id === id)).toEqual([]);
  });
});

describe("voice clips replay the recorded pipeline", () => {
  it("adds each clip's entries to the session, in order", async () => {
    const id = await startSession();
    const res = await recordClip(id);
    expect(res.status).toBe(201);
    const recorded = fixture.session_clips[0].response;
    expect(res.body.data.transcript).toBe(recorded.transcript);
    expect(res.body.data.entries_created).toHaveLength(recorded.entries_created.length);
    const created = res.body.data.entries_created[0];
    expect(created).toMatchObject({
      session_id: id,
      client_id: sarah.id,
      sequence_order: 1,
      exercise_canonical: "Goblet Squat",
    });
    expect(created.id).not.toBe(recorded.entries_created[0].id);

    await recordClip(id); // the knee note about the squats
    await recordClip(id);
    const entries = (await call("GET", `/sessions/${id}/entries`)).body.data;
    expect(
      entries.map((e: { entry_type: string; exercise_canonical: string | null }) =>
        e.entry_type === "exercise_card" ? e.exercise_canonical : "note",
      ),
    ).toEqual(["Goblet Squat", "note", "Romanian Deadlift"]);
  });

  it("applies a correction to the entry it corrects", async () => {
    const id = await startSession();
    for (let i = 0; i < 4; i++) await recordClip(id); // clip 4: "that last set was 30 kilos"
    const rdl = getState().entries.find(
      (e) => e.session_id === id && e.exercise_canonical === "Romanian Deadlift",
    )!;
    expect(rdl.sets!.map((s) => s.weight)).toEqual([25, 25, 30]);
  });

  it("skips a correction whose entry was deleted", async () => {
    const id = await startSession();
    await recordClip(id);
    await recordClip(id);
    const rdl = (await recordClip(id)).body.data.entries_created[0];
    await call("DELETE", `/entries/${rdl.id}`);
    const res = await recordClip(id); // "that last set was 30 kilos"
    expect(res.body.data.entries_modified).toEqual([]);
  });

  it("keeps each session's clips separate", async () => {
    const a = await startSession();
    const b = await startSession();
    await recordClip(a);
    const first = await recordClip(b);
    expect(first.body.data.transcript).toBe(fixture.session_clips[0].response.transcript);
  });

  it("starts over after the last sample clip", async () => {
    const id = await startSession();
    for (let i = 0; i < fixture.session_clips.length; i++) await recordClip(id);
    const again = await recordClip(id);
    expect(again.body.data.transcript).toBe(fixture.session_clips[0].response.transcript);
  });

  it("explains that typed entries are not available", async () => {
    const id = await startSession();
    const res = await call("POST", `/sessions/${id}/text-entry`, { text: "squats 3x10" });
    expect(res.status).toBe(422);
    expect(res.body.error.message).toMatch(/record button/);
  });
});

describe("entries", () => {
  it("recalculates volume when sets change", async () => {
    const id = await startSession();
    const entry = (await recordClip(id)).body.data.entries_created[0];
    const res = await call("PATCH", `/entries/${entry.id}`, {
      sets: [
        { reps: 10, weight: 20 },
        { reps: 8, weight: 22.5 },
      ],
    });
    expect(res.body.data.total_volume_kg).toBe(380);
  });

  it("creates a manual entry at the end of the session", async () => {
    const id = await startSession();
    await recordClip(id);
    const res = await call("POST", `/sessions/${id}/entries`, {
      entry_type: "observation_card",
      observation_text: "Good energy today",
    });
    expect(res.status).toBe(201);
    expect(res.body.data).toMatchObject({
      sequence_order: 2,
      observation_text: "Good energy today",
      exercise_name: null,
    });
  });
});

describe("totalVolume", () => {
  it("sums reps × weight, reading weight_kg too", () => {
    expect(
      totalVolume([
        { reps: 10, rpe: null, weight: 20 },
        { reps: 5, weight_kg: 10 } as never,
      ]),
    ).toBe(250);
  });

  it("is null when no set has a weight", () => {
    expect(totalVolume([{ reps: 12 }, { reps: 12 }] as never)).toBeNull();
  });
});

describe("workout_type", () => {
  it("labels a session by its exercises, as it changes", async () => {
    const id = await startSession();
    const label = async () =>
      (await call("GET", `/sessions/${id}`)).body.data.workout_type;
    expect(await label()).toBe("Session");
    for (let i = 0; i < 3; i++) await recordClip(id);
    expect(await label()).toBe("Lower Body");
    for (let i = 0; i < 3; i++) await recordClip(id); // + push-ups and plank
    expect(await label()).toBe("Full Body");
  });

  it("labels every session in a list", async () => {
    const { body } = await call("GET", `/clients/${sarah.id}/sessions`);
    for (const s of body.data) expect(typeof s.workout_type).toBe("string");
  });
});

describe("summary", () => {
  const endSession = (id: string) =>
    call("PATCH", `/sessions/${id}`, { ended_at: new Date().toISOString() });
  const summary = async (id: string) => call("POST", `/sessions/${id}/summary`, {});
  const recordedFor = (clientId: string, clips: number) =>
    (
      fixture.session_clip_summaries as Record<
        string,
        Array<{ ai_summary: string | null }>
      >
    )[clientId][clips - 1].ai_summary;

  it("refuses a session that hasn't ended", async () => {
    const id = await startSession();
    expect((await summary(id)).status).toBe(409);
  });

  it("replays this client's summary for the clips recorded", async () => {
    const id = await startSession();
    await recordClip(id);
    await recordClip(id);
    await endSession(id);
    const res = await summary(id);
    expect(res.body.data.ai_summary).toBe(recordedFor(sarah.id, 2));
    expect((await call("GET", `/sessions/${id}`)).body.data.ai_summary).toBe(
      recordedFor(sarah.id, 2),
    );
  });

  it("uses the last recorded summary once the clips start over", async () => {
    const id = await startSession();
    for (let i = 0; i < fixture.session_clips.length + 2; i++) await recordClip(id);
    await endSession(id);
    expect((await summary(id)).body.data.ai_summary).toBe(
      recordedFor(sarah.id, fixture.session_clips.length),
    );
  });

  it("has none for a session with no clips", async () => {
    const id = await startSession();
    await endSession(id);
    expect((await summary(id)).body.data.ai_summary).toBeNull();
  });

  it("keeps a seeded session's own summary", async () => {
    const seeded = fixture.sessions.find((s) => s.ended_at && s.ai_summary)!;
    expect((await summary(seeded.id)).body.data.ai_summary).toBe(seeded.ai_summary);
  });

  it("was recorded for every client and every number of clips", () => {
    for (const client of fixture.clients) {
      const recordings = (fixture.session_clip_summaries as Record<string, unknown[]>)[
        client.id
      ];
      expect(recordings).toHaveLength(fixture.session_clips.length);
    }
  });
});

describe("brain", () => {
  it("answers each suggested question with the recorded answer", async () => {
    for (const { question, answer } of fixture.brain) {
      const res = await call("POST", "/brain/ask", {
        question: ` ${question.toLowerCase()} `,
      });
      expect(res.body.data.answer).toBe(answer);
    }
  });

  it("explains that other questions aren't available", async () => {
    const res = await call("POST", "/brain/ask", {
      question: "What's Sarah's max deadlift?",
    });
    expect(res.status).toBe(422);
    expect(res.body.error.message).toMatch(/suggested questions/);
  });
});

describe("plans", () => {
  it("transcribes and parses the sample dictation", async () => {
    const { transcript } = (await call("POST", "/transcribe")).body.data;
    expect(transcript).toBe(fixture.plan_clip.transcript);
    const parsed = await call("POST", "/plans/parse", {
      text: `  ${transcript.toUpperCase()} `,
    });
    expect(parsed.body.data).toEqual(fixture.plan_clip.parsed);
  });

  it("explains that typed plans are not available", async () => {
    const res = await call("POST", "/plans/parse", { text: "squats 5x5" });
    expect(res.status).toBe(422);
    expect(res.body.error.message).toMatch(/mic/);
  });

  it("creates, edits and deletes a plan", async () => {
    const created = (
      await call("POST", "/plans", { client_id: sarah.id, plan_text: "Legs" })
    ).body.data;
    expect((await call("GET", `/clients/${sarah.id}/plans`)).body.data[0].id).toBe(
      created.id,
    );
    expect(
      (await call("PATCH", `/plans/${created.id}`, { plan_text: "Legs and core" })).body
        .data.plan_text,
    ).toBe("Legs and core");
    expect((await call("DELETE", `/plans/${created.id}`)).status).toBe(204);
    expect((await call("GET", `/plans/${created.id}`)).status).toBe(404);
  });
});

it("answers an unknown route with 404", async () => {
  expect((await call("GET", "/brain/conversations")).status).toBe(404);
});
