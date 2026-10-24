/**
 * The demo's database: the recorded seed data, kept in this browser.
 *
 * Each visitor gets their own copy in localStorage, so what they record is
 * still there when they come back, and nobody sees anyone else's sessions.
 * If storage is unavailable (private window, blocked site data) the copy
 * lives in memory for the visit instead.
 */

import type { Client, Session, SessionEntry, SessionPlan } from "@/src/api/types";

import fixture from "./fixture.json";

export interface DemoState {
  /** fixture.captured_at and the day it was made: a re-recorded fixture, or a
   *  new day (today's schedule has moved on), replaces a saved copy */
  version: string;
  clients: Client[];
  sessions: Session[];
  entries: SessionEntry[];
  plans: SessionPlan[];
  /** Sample clips replayed so far, per session */
  clipsUsed: Record<string, number>;
  /** Per session: recorded entry id → the id it got in this session, so a later
   *  clip that corrects an earlier one ("actually that was 30 kilos") finds it */
  replayIds: Record<string, Record<string, string>>;
}

const STORAGE_KEY = "supertrainer-demo";
const DAY_MS = 24 * 60 * 60 * 1000;
const QUARTER_HOUR_MS = 15 * 60 * 1000;

// Local start time for each client's sessions, in hours. The seed stamps every
// session with the time the seed ran (late at night), which no gym keeps.
const SESSION_HOURS = [7, 9.5, 12, 17.5, 18.5];

const shiftIso = (iso: string | null, ms: number) =>
  iso === null ? null : new Date(new Date(iso).getTime() + ms).toISOString();

function shiftDate(date: string | null, days: number): string | null {
  if (date === null) return null;
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Move the recorded data so it reads as recent: the most recent seeded day
 * becomes today (so the home screen opens on today's sessions), earlier days
 * keep their spacing, and each session starts at its client's usual hour.
 */
export function freshen(now: Date): DemoState {
  const capturedAt = new Date(fixture.captured_at).getTime();
  const daysBeforeCapture = (iso: string) =>
    Math.round((capturedAt - new Date(iso).getTime()) / DAY_MS);
  const latestDay = Math.min(
    ...fixture.sessions.map((s) => daysBeforeCapture(s.started_at)),
  );
  const shiftMs = now.getTime() - capturedAt + latestDay * DAY_MS;
  const shiftDays = Math.round(shiftMs / DAY_MS);
  const todayMidnight = new Date(now);
  todayMidnight.setHours(0, 0, 0, 0);

  const clientIndex = new Map(fixture.clients.map((c, i) => [c.id, i]));
  const sessionMoves = new Map<string, { oldStart: number; newStart: number }>();

  const sessions = (fixture.sessions as Session[]).map((s) => {
    const oldStart = new Date(s.started_at).getTime();
    const day = new Date(todayMidnight);
    day.setDate(day.getDate() - (daysBeforeCapture(s.started_at) - latestDay));
    const hour =
      SESSION_HOURS[(clientIndex.get(s.client_id) ?? 0) % SESSION_HOURS.length];
    let newStart = day.getTime() + hour * 60 * 60 * 1000;
    // A finished session today must have finished already
    const lengthMs = (s.duration_minutes ?? 60) * 60_000;
    const latestStart =
      Math.floor((now.getTime() - lengthMs) / QUARTER_HOUR_MS) * QUARTER_HOUR_MS -
      QUARTER_HOUR_MS;
    if (newStart > latestStart && latestStart >= todayMidnight.getTime())
      newStart = latestStart;
    sessionMoves.set(s.id, { oldStart, newStart });
    const move = newStart - oldStart;
    return {
      ...s,
      started_at: new Date(newStart).toISOString(),
      ended_at: shiftIso(s.ended_at, move),
      scheduled_for: shiftIso(s.scheduled_for, move),
      created_at: shiftIso(s.created_at, move)!,
      updated_at: shiftIso(s.updated_at, move)!,
    };
  });

  const entries = (fixture.entries as SessionEntry[]).map((e) => {
    const m = sessionMoves.get(e.session_id);
    const move = m ? m.newStart - m.oldStart : shiftMs;
    return {
      ...e,
      performed_at: shiftIso(e.performed_at, move),
      created_at: shiftIso(e.created_at, move)!,
    };
  });

  return {
    version: versionFor(now),
    sessions: [...sessions, ...upcomingSessions(now, todayMidnight, sessions)],
    clients: (fixture.clients as Client[]).map((c) => ({
      ...c,
      created_at: shiftIso(c.created_at, shiftMs)!,
    })),
    entries,
    plans: (fixture.plans as SessionPlan[]).map((p) => ({
      ...p,
      planned_for_date: shiftDate(p.planned_for_date, shiftDays),
      created_at: shiftIso(p.created_at, shiftMs)!,
    })),
    clipsUsed: {},
    replayIds: {},
  };
}

/**
 * A session later today for each client who hasn't trained today, so the home
 * screen opens on a day still to coach, each session with its AI notes.
 * 75 minutes apart from half an hour from now, rounded to the quarter hour;
 * late in the evening they're squeezed in between now and midnight instead.
 */
export function upcomingSessions(
  now: Date,
  todayMidnight: Date,
  sessions: Session[],
): Session[] {
  const trainedToday = new Set(
    sessions
      .filter((s) => new Date(s.started_at).getTime() >= todayMidnight.getTime())
      .map((s) => s.client_id),
  );
  const waiting = (fixture.clients as Client[]).filter((c) => !trainedToday.has(c.id));
  const endOfDay = todayMidnight.getTime() + DAY_MS - 60_000;
  const first =
    Math.ceil((now.getTime() + 30 * 60_000) / QUARTER_HOUR_MS) * QUARTER_HOUR_MS;
  const roomy = first + (waiting.length - 1) * 75 * 60_000 <= endOfDay;
  const gap = (endOfDay - now.getTime()) / (waiting.length + 1);
  const slot = (i: number) =>
    roomy ? first + i * 75 * 60_000 : now.getTime() + (i + 1) * gap;
  return waiting.map((client, i) => {
    const at = new Date(slot(i)).toISOString();
    return {
      id: `upcoming-${client.id}`,
      trainer_id: client.trainer_id,
      client_id: client.id,
      started_at: at,
      scheduled_for: at,
      plan_id: null,
      ended_at: null,
      duration_minutes: null,
      audio_url: null,
      audio_duration_seconds: null,
      raw_transcript: null,
      processing_status: "pending",
      trainer_edited: false,
      ai_summary: null,
      workout_type: "Session",
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    };
  });
}

const versionFor = (day: Date) => `${fixture.captured_at}|${day.toDateString()}`;

function load(): DemoState | null {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as DemoState;
    return saved.version === versionFor(new Date()) ? saved : null;
  } catch {
    return null;
  }
}

let state: DemoState | null = null;

export function getState(): DemoState {
  if (!state) state = load() ?? freshen(new Date());
  return state;
}

export function save(): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(getState()));
  } catch {
    // Storage full or blocked — the in-memory copy still works for this visit
  }
}

/** Back to the recorded data, as on a first visit. */
export function resetDemo(): void {
  state = freshen(new Date());
  save();
}

export function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `demo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}
