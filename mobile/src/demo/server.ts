/**
 * The backend, inside the browser, for the web demo.
 *
 * `demoFetch` has fetch's signature and answers the same /api/v1 routes the
 * app calls, with the same response shapes, so src/api/client.ts swaps it in
 * and nothing else in the app changes. Rules (ordering, pagination, defaults,
 * volume) mirror backend/app/api and backend/app/services.
 *
 * Voice clips and plan parsing need Deepgram and Claude, which the demo can't
 * call. Those routes replay what the real pipeline returned for the sample
 * clips (recorded by backend/scripts/export_web_demo.py), at the speed it ran.
 */

import type {
  Client,
  Session,
  SessionEntry,
  SessionPlan,
  SetData,
  VoiceClipResponse,
} from "@/src/api/types";

import { classifyWorkout } from "./classify";
import fixture from "./fixture.json";
import { getState, newId, save } from "./store";

// ---------------------------------------------------------------------------
// Responses
// ---------------------------------------------------------------------------

class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const notFound = (what: string) => new HttpError(404, `${what} not found`);

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const data = (value: unknown, status = 200) => json({ data: value, meta: {} }, status);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------------------------------------------------------------------------
// Helpers mirroring the backend services
// ---------------------------------------------------------------------------

/** services/pagination.py: sort key DESC, id ASC; cursor = last id of the previous page. */
function paginate<T extends { id: string }>(
  items: T[],
  sortKey: keyof T,
  query: URLSearchParams,
) {
  const limit = Number(query.get("limit") ?? 20);
  const sorted = [...items].sort((a, b) => {
    const ka = String(a[sortKey]);
    const kb = String(b[sortKey]);
    if (ka !== kb) return ka < kb ? 1 : -1;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
  const cursor = query.get("cursor");
  const start = cursor ? sorted.findIndex((item) => item.id === cursor) + 1 : 0;
  const page = sorted.slice(start, start + limit);
  const hasMore = sorted.length > start + limit;
  return json({
    data: page,
    meta: {
      cursor: page.length ? page[page.length - 1].id : null,
      limit,
      has_more: hasMore,
    },
  });
}

/** The services' PATCH rule: fields sent as null are skipped, not cleared. */
function applyPatch<T extends object>(target: T, patch: Record<string, unknown>): T {
  for (const [key, value] of Object.entries(patch)) {
    if (value !== null && value !== undefined)
      (target as Record<string, unknown>)[key] = value;
  }
  return target;
}

/** services/entry_service.py: sum of reps × weight, null when no set has a weight. */
export function totalVolume(sets: SetData[]): number | null {
  let total = 0;
  let hasWeight = false;
  for (const s of sets as Array<SetData & { weight_kg?: number }>) {
    const w = s.weight || s.weight_kg;
    if (w !== null && w !== undefined) {
      total += (s.reps || 0) * w;
      hasWeight = true;
    }
  }
  return hasWeight ? Math.round(total * 10) / 10 : null;
}

/** The calendar date of `iso` in IANA zone `tz`, as YYYY-MM-DD. */
function localDate(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz }).format(new Date(iso));
}

function findOr404<T extends { id: string }>(items: T[], id: string, what: string): T {
  const item = items.find((i) => i.id === id);
  if (!item) throw notFound(what);
  return item;
}

function nextSequenceOrder(sessionId: string): number {
  const orders = getState()
    .entries.filter((e) => e.session_id === sessionId)
    .map((e) => e.sequence_order);
  return Math.max(0, ...orders) + 1;
}

function newEntry(session: Session, fields: Partial<SessionEntry>): SessionEntry {
  const now = new Date().toISOString();
  return {
    exercise_name: null,
    exercise_canonical: null,
    sets: null,
    total_volume_kg: null,
    form_notes: null,
    cues_given: null,
    cue_effectiveness: null,
    observation_text: null,
    attached_to_set: null,
    flag_color: null,
    flag_reason: null,
    performed_at: null,
    entry_type: "exercise_card",
    ...fields,
    id: newId(),
    session_id: session.id,
    client_id: session.client_id,
    sequence_order: fields.sequence_order ?? nextSequenceOrder(session.id),
    created_at: now,
  };
}

// ---------------------------------------------------------------------------
// Replayed pipeline
// ---------------------------------------------------------------------------

type RecordedEntry = SessionEntry;
const sessionClips = fixture.session_clips as Array<{
  audio: string;
  response: VoiceClipResponse & {
    entries_created: RecordedEntry[];
    entries_modified: RecordedEntry[];
  };
}>;

/** The sample clip the next recording in this session plays and replays. */
export function nextSessionClip(sessionId: string) {
  const used = getState().clipsUsed[sessionId] ?? 0;
  return sessionClips[used % sessionClips.length];
}

// Fields a recorded correction carries over; ids and timestamps stay the live entry's
const REPLAY_SKIP = new Set([
  "id",
  "session_id",
  "client_id",
  "sequence_order",
  "created_at",
  "performed_at",
]);

async function replayVoiceClip(session: Session) {
  const state = getState();
  const clip = nextSessionClip(session.id);
  state.clipsUsed[session.id] = (state.clipsUsed[session.id] ?? 0) + 1;
  const replayIds = (state.replayIds[session.id] ??= {});

  await sleep(clip.response.timing.total_ms);

  const created = clip.response.entries_created.map((recorded) => {
    const entry = newEntry(session, {
      ...recorded,
      sequence_order: undefined,
      performed_at: new Date().toISOString(),
    });
    replayIds[recorded.id] = entry.id;
    state.entries.push(entry);
    return entry;
  });

  // A correction whose target the visitor already deleted has nothing to change
  const modified = clip.response.entries_modified.flatMap((recorded) => {
    const live = state.entries.find((e) => e.id === replayIds[recorded.id]);
    if (!live) return [];
    for (const [key, value] of Object.entries(recorded)) {
      if (!REPLAY_SKIP.has(key))
        (live as unknown as Record<string, unknown>)[key] = value;
    }
    return [live];
  });

  save();
  return data(
    { ...clip.response, entries_created: created, entries_modified: modified },
    201,
  );
}

const normalize = (text: string) => text.trim().toLowerCase().replace(/\s+/g, " ");

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

interface DemoRequest {
  query: URLSearchParams;
  body: Record<string, unknown>;
}

type Handler = (params: string[], req: DemoRequest) => Response | Promise<Response>;

const routes: Array<[string, RegExp, Handler]> = [
  // --- Clients ---
  [
    "GET",
    /^\/clients$/,
    (_, { query }) => {
      const all = getState().clients;
      const visible =
        query.get("include_archived") === "true" ? all : all.filter((c) => !c.archived);
      return paginate(visible, "created_at", query);
    },
  ],
  [
    "POST",
    /^\/clients$/,
    (_, { body }) => {
      const state = getState();
      const client: Client = {
        email: null,
        phone: null,
        birth_date: null,
        training_start_date: null,
        goals: null,
        injury_history: null,
        ...(body as Partial<Client>),
        preferred_weight_unit:
          (body.preferred_weight_unit as Client["preferred_weight_unit"]) ?? "kg",
        archived: false,
        id: newId(),
        trainer_id: state.clients[0].trainer_id,
        created_at: new Date().toISOString(),
      } as Client;
      state.clients.push(client);
      save();
      return data(client, 201);
    },
  ],
  [
    "GET",
    /^\/clients\/([^/]+)$/,
    ([id]) => data(findOr404(getState().clients, id, "Client")),
  ],
  [
    "PATCH",
    /^\/clients\/([^/]+)$/,
    ([id], { body }) => {
      const client = applyPatch(findOr404(getState().clients, id, "Client"), body);
      save();
      return data(client);
    },
  ],
  [
    "GET",
    /^\/clients\/([^/]+)\/sessions$/,
    ([id], { query }) => {
      findOr404(getState().clients, id, "Client");
      return paginate(
        getState().sessions.filter((s) => s.client_id === id),
        "started_at",
        query,
      );
    },
  ],
  [
    "GET",
    /^\/clients\/([^/]+)\/entries$/,
    ([id], { query }) => {
      findOr404(getState().clients, id, "Client");
      return paginate(
        getState().entries.filter((e) => e.client_id === id),
        "created_at",
        query,
      );
    },
  ],
  [
    "GET",
    /^\/clients\/([^/]+)\/plans$/,
    ([id], { query }) => {
      findOr404(getState().clients, id, "Client");
      return paginate(
        getState().plans.filter((p) => p.client_id === id),
        "created_at",
        query,
      );
    },
  ],

  // --- Sessions ---
  [
    "GET",
    /^\/sessions$/,
    (_, { query }) => {
      const date = query.get("scheduled_for_date");
      const tz = query.get("tz") ?? "UTC";
      const sessions = getState().sessions.filter(
        (s) =>
          !date ||
          localDate(s.started_at, tz) === date ||
          (s.scheduled_for !== null && localDate(s.scheduled_for, tz) === date),
      );
      return paginate(sessions, "started_at", query);
    },
  ],
  [
    "POST",
    /^\/sessions$/,
    (_, { body }) => {
      const state = getState();
      const client = findOr404(state.clients, String(body.client_id), "Client");
      if (body.plan_id) {
        const plan = findOr404(state.plans, String(body.plan_id), "Session plan");
        if (plan.client_id !== client.id)
          throw new HttpError(422, "Plan does not belong to this client");
      }
      const now = new Date().toISOString();
      const session: Session = {
        id: newId(),
        trainer_id: client.trainer_id,
        client_id: client.id,
        started_at: String(body.started_at),
        scheduled_for: (body.scheduled_for as string) ?? null,
        plan_id: (body.plan_id as string) ?? null,
        ended_at: null,
        duration_minutes: null,
        audio_url: null,
        audio_duration_seconds: null,
        raw_transcript: null,
        processing_status: "pending",
        trainer_edited: false,
        created_at: now,
        updated_at: now,
      };
      state.sessions.push(session);
      save();
      return data(session, 201);
    },
  ],
  [
    "GET",
    /^\/sessions\/([^/]+)$/,
    ([id]) => data(findOr404(getState().sessions, id, "Session")),
  ],
  [
    "PATCH",
    /^\/sessions\/([^/]+)$/,
    ([id], { body }) => {
      const session = findOr404(getState().sessions, id, "Session");
      const patch = { ...body };
      // Auto-compute duration when ending a session
      if (typeof patch.ended_at === "string") {
        const ms =
          new Date(patch.ended_at).getTime() - new Date(session.started_at).getTime();
        patch.duration_minutes = Math.max(0, Math.round(ms / 60_000));
      }
      applyPatch(session, { ...patch, updated_at: new Date().toISOString() });
      save();
      return data(session);
    },
  ],
  [
    "DELETE",
    /^\/sessions\/([^/]+)$/,
    ([id]) => {
      const state = getState();
      findOr404(state.sessions, id, "Session");
      state.sessions = state.sessions.filter((s) => s.id !== id);
      state.entries = state.entries.filter((e) => e.session_id !== id);
      save();
      return new Response(null, { status: 204 });
    },
  ],
  [
    "POST",
    /^\/sessions\/([^/]+)\/classify$/,
    ([id]) => {
      findOr404(getState().sessions, id, "Session");
      const names = getState()
        .entries.filter((e) => e.session_id === id && e.entry_type === "exercise_card")
        .flatMap((e) => (e.exercise_canonical ? [e.exercise_canonical] : []));
      return data({ workout_type: classifyWorkout(names, fixture.exercise_regions) });
    },
  ],
  [
    "GET",
    /^\/sessions\/([^/]+)\/entries$/,
    ([id]) => {
      findOr404(getState().sessions, id, "Session");
      const entries = getState()
        .entries.filter((e) => e.session_id === id)
        .sort((a, b) => a.sequence_order - b.sequence_order);
      return json({ data: entries, meta: { cursor: null, limit: 20, has_more: false } });
    },
  ],
  [
    "POST",
    /^\/sessions\/([^/]+)\/entries$/,
    ([id], { body }) => {
      const entry = newEntry(
        findOr404(getState().sessions, id, "Session"),
        body as Partial<SessionEntry>,
      );
      getState().entries.push(entry);
      save();
      return data(entry, 201);
    },
  ],
  [
    "POST",
    /^\/sessions\/([^/]+)\/voice-clip$/,
    ([id]) => replayVoiceClip(findOr404(getState().sessions, id, "Session")),
  ],
  [
    "POST",
    /^\/sessions\/([^/]+)\/text-entry$/,
    () => {
      throw new HttpError(
        422,
        "Typed entries need the live AI parser, which this demo doesn't run. Try the record button.",
      );
    },
  ],

  // --- Entries ---
  [
    "GET",
    /^\/entries\/([^/]+)$/,
    ([id]) => data(findOr404(getState().entries, id, "Entry")),
  ],
  [
    "PATCH",
    /^\/entries\/([^/]+)$/,
    ([id], { body }) => {
      const entry = applyPatch(findOr404(getState().entries, id, "Entry"), body);
      if (Array.isArray(body.sets))
        entry.total_volume_kg = totalVolume(body.sets as SetData[]);
      save();
      return data(entry);
    },
  ],
  [
    "DELETE",
    /^\/entries\/([^/]+)$/,
    ([id]) => {
      const state = getState();
      findOr404(state.entries, id, "Entry");
      state.entries = state.entries.filter((e) => e.id !== id);
      save();
      return new Response(null, { status: 204 });
    },
  ],

  // --- Plans ---
  [
    "POST",
    /^\/plans\/parse$/,
    async (_, { body }) => {
      if (
        normalize(String(body.text ?? "")) !== normalize(fixture.plan_clip.transcript)
      ) {
        throw new HttpError(
          422,
          "Typed plans need the live AI parser, which this demo doesn't run. Tap the mic to try a sample dictation.",
        );
      }
      await sleep(1500);
      return data(fixture.plan_clip.parsed);
    },
  ],
  [
    "POST",
    /^\/plans$/,
    (_, { body }) => {
      const state = getState();
      const client = findOr404(state.clients, String(body.client_id), "Client");
      const plan: SessionPlan = {
        id: newId(),
        trainer_id: client.trainer_id,
        client_id: client.id,
        plan_text: String(body.plan_text),
        planned_exercises:
          (body.planned_exercises as SessionPlan["planned_exercises"]) ?? null,
        planned_for_date: (body.planned_for_date as string) ?? null,
        created_at: new Date().toISOString(),
      };
      state.plans.push(plan);
      save();
      return data(plan, 201);
    },
  ],
  [
    "GET",
    /^\/plans\/([^/]+)$/,
    ([id]) => data(findOr404(getState().plans, id, "Session plan")),
  ],
  [
    "PATCH",
    /^\/plans\/([^/]+)$/,
    ([id], { body }) => {
      const plan = applyPatch(findOr404(getState().plans, id, "Session plan"), body);
      save();
      return data(plan);
    },
  ],
  [
    "DELETE",
    /^\/plans\/([^/]+)$/,
    ([id]) => {
      const state = getState();
      findOr404(state.plans, id, "Session plan");
      state.plans = state.plans.filter((p) => p.id !== id);
      save();
      return new Response(null, { status: 204 });
    },
  ],

  // --- Transcription (plan dictation) ---
  [
    "POST",
    /^\/transcribe$/,
    async () => {
      await sleep(800);
      return data({ transcript: fixture.plan_clip.transcript });
    },
  ],
];

const API_PREFIX = "/api/v1";

export async function demoFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const url = new URL(input, "http://demo.local");
  const method = (init.method ?? "GET").toUpperCase();
  const path = url.pathname.startsWith(API_PREFIX)
    ? url.pathname.slice(API_PREFIX.length)
    : url.pathname;
  const body = typeof init.body === "string" ? JSON.parse(init.body) : {};

  try {
    for (const [routeMethod, pattern, handler] of routes) {
      const match = method === routeMethod ? pattern.exec(path) : null;
      if (match) return await handler(match.slice(1), { query: url.searchParams, body });
    }
    throw notFound("Route");
  } catch (err) {
    if (err instanceof HttpError) {
      return json(
        { error: { code: `http_${err.status}`, message: err.message } },
        err.status,
      );
    }
    throw err;
  }
}
