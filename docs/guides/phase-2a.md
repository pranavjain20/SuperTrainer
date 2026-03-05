# Phase 2a Walkthrough — Building the Mobile App

Phase 1a built the database. Phase 1b built the voice pipeline that fills it. Phase 2a built the thing a trainer actually touches — a React Native app that ties it all together. Record voice, see structured data appear, edit inline, browse client history.

This was the biggest phase yet: 12 days, 7 screens, 22 components, 10 hooks, and a design system overhaul. Here's how it all works.

---

## The Big Picture

A trainer opens the app. They see today's sessions on the home screen. They tap a client name to browse their profile — goals, session history, plans. When it's time for a session, they tap "Start Session," the app goes into recording mode, and they start speaking. Every voice clip gets sent to the backend (Deepgram → Claude → validation), and structured exercise and observation cards appear on a live timeline. The trainer can tap any card to edit it inline. When the session is done, they see a summary with stats and workout classification.

The entire interaction is: speak → see cards → fix anything wrong → end session. No typing required during the workout.

---

## Navigation — Why File-Based Routing Changes Everything

React Native navigation is traditionally configured in code — you define screens, stacks, and tabs in JavaScript objects. Expo Router takes a completely different approach: **the file system IS the navigation structure.**

```
app/
├── _layout.tsx              ← Root stack (wraps everything)
├── (tabs)/                  ← Tab navigator
│   ├── _layout.tsx          ← Tab bar configuration
│   ├── index.tsx            ← Home tab
│   ├── brain.tsx            ← Brain tab (Phase 3)
│   ├── clients/
│   │   ├── _layout.tsx      ← Stack inside Clients tab
│   │   ├── index.tsx        ← Client list
│   │   └── [id].tsx         ← Client profile (dynamic)
│   └── session/
│       ├── _layout.tsx      ← Stack inside Sessions tab
│       └── index.tsx        ← All sessions list
└── recording/
    ├── _layout.tsx          ← Recording stack
    └── [sessionId].tsx      ← Active recording screen
```

Every `.tsx` file in `app/` becomes a route automatically. Folders with `_layout.tsx` become navigators. The `(tabs)` folder name (with parentheses) is a special Expo Router convention — it creates a tab navigator without affecting the URL path.

### The Recording Screen Lives Outside Tabs

This is a deliberate architectural decision. The recording screen is at `app/recording/[sessionId].tsx`, outside the `(tabs)` group. Why?

When a trainer is recording a session, they need the full screen. No tab bar eating up space. No accidental tab switches mid-recording. By placing it outside the tab navigator, it renders as a full-screen modal on top of everything.

But this creates a problem: what if the trainer is on the Clients tab and tries to switch to Home while recording? The tab layout in `(tabs)/_layout.tsx` intercepts tab presses with `tabPress` event listeners. If `isRecording` is true (from the Zustand store), it shows an Alert: "Stop & Leave" or "Keep Recording." This prevents accidental navigation away from an active session.

The root layout also disables the iOS swipe-back gesture during recording (`gestureEnabled: !isRecording`), so a trainer can't accidentally swipe away and lose their session state.

### Dynamic Routes — The `[id]` Convention

`[id].tsx` and `[sessionId].tsx` use square brackets to indicate dynamic segments. When you navigate to `/clients/abc-123`, Expo Router renders `[id].tsx` and makes `abc-123` available via `useLocalSearchParams()`. This is the same concept as Express.js route parameters or Next.js dynamic routes.

---

## The API Layer — Three Levels of Abstraction

The mobile app talks to the backend through a clean three-layer API architecture. Each layer has one job.

### Layer 1: HTTP Primitives (`src/api/client.ts`)

Five functions: `apiGet`, `apiPost`, `apiPatch`, `apiDelete`, `apiUpload`. They handle the raw HTTP mechanics — constructing URLs, setting headers, parsing JSON, throwing typed errors.

All five share one `handleResponse<T>` helper. It checks the HTTP status, extracts our standard error envelope (`{"error": {"code": "...", "message": "..."}}`), and throws a typed `ApiError` with the code and message. This means every downstream caller gets clean, typed errors instead of raw fetch responses.

`apiUpload` is special — it deliberately omits the `Content-Type` header. When you send a `FormData` object via fetch, the browser/runtime needs to set the Content-Type to `multipart/form-data` with a generated boundary string. If you set it manually, you'd need to also generate the boundary, which is fragile. Omitting it lets fetch handle it automatically.

### Layer 2: Domain Endpoints (`src/api/clients.ts`, `sessions.ts`, etc.)

Each file wraps the primitives with domain-specific functions: `getClient(id)`, `createSession(data)`, `processVoiceClip(sessionId, audioUri)`. They handle the URL construction and response unwrapping.

Single-resource functions unwrap the `data` field and return `T` directly. List functions return the full `ListResponse<T>` so callers can access pagination metadata (`cursor`, `has_more`).

### Layer 3: React Hooks (`src/hooks/`)

Hooks wrap the endpoint functions with TanStack Query for caching, deduplication, and automatic refetching. More on this in the state management section.

### Why Three Layers?

Because each layer changes for different reasons:
- If we switch from fetch to axios, only Layer 1 changes.
- If a backend URL changes, only Layer 2 changes.
- If we want different cache behavior, only Layer 3 changes.

Nothing is tangled. A bug in caching can't break HTTP handling. A URL change can't break rendering logic.

---

## TypeScript Types — Mirroring the Backend

`src/api/types.ts` defines TypeScript interfaces for every backend Pydantic schema. `Client`, `Session`, `SessionEntry`, `SessionPlan`, `InjuryFlag` — each with Create and Update variants.

### The SetData Problem

The most interesting type is `SetData`, which represents one set within an exercise card. The challenge: **two different backend producers write sets in different formats.**

The seed script (Phase 1a) writes:
```json
{"set": 1, "reps": 10, "weight_kg": 55}
```

The voice pipeline (Phase 1b) writes:
```json
{"reps": 10, "weight": 55, "weight_unit": "kg"}
```

No `set` field. `weight` instead of `weight_kg`. Different keys for the same concept.

Why? Because the `sets` field on `session_entries` is a JSONB column — a raw JSON blob with no enforced schema. Each producer writes whatever structure makes sense for its context. The Pydantic schema says `sets: list[dict]`. There's no validation on the shape of individual set objects.

The solution isn't to "fix" the types — it's to handle both formats explicitly. Utility functions like `getSetWeight(set)` check for `weight_kg` first, then `weight`, then `weight` with unit conversion. `getSetNumber(set, index)` checks for `set`, then `set_number`, then falls back to `index + 1`.

This is a lesson worth internalizing: **TypeScript types describe the interface you want. The backend describes reality. Build from reality.** When the two disagree, reality wins.

---

## State Management — Two Systems, Clear Boundaries

The app uses two state management tools. They never overlap.

### TanStack Query — Server State

TanStack Query (formerly React Query) handles everything that lives on the server: clients, sessions, entries, plans. It provides:

- **Caching**: Fetch once, use everywhere. If two screens both need the client list, only one API call is made.
- **Stale time**: Each resource type has a tuned `staleTime` — how long the cached data is considered fresh. Clients rarely change mid-session (5 minutes). Session entries change on every voice clip (10 seconds). Home screen sessions need to feel current (1 minute).
- **Automatic refetching**: When data goes stale and a component re-renders, TanStack refetches in the background. The UI shows cached data immediately, then updates when fresh data arrives.
- **Query key hierarchy**: Keys like `["clients"]`, `["clients", id]`, `["entries", "session", sessionId]` enable precise invalidation. After a voice clip upload, we invalidate `["entries", "session", sessionId]` — only that session's entries refetch, not everything.
- **Optimistic updates**: After editing an entry inline, `setQueryData` patches the cache immediately so the UI updates before the server responds. No spinner, no lag — the edit feels instant.

### Zustand — UI State

Zustand handles state that doesn't live on the server and needs to be shared across components:

**`recordingStore`** — Global, persists across navigation. Holds `isRecording` (used by tab layout guards and root layout gesture control), `activeSessionId` / `activeClientName` / `activeSessionStartedAt` (drives the `ActiveSessionBanner`), and a `stopRecording` function reference.

That last one is clever: the tab layout needs to stop recording when the trainer confirms "Stop & Leave," but it can't import expo-av (that would create a coupling nightmare). Instead, `useVoiceRecorder` registers its own `stopRecording` function into the store on mount. The tab layout calls `recordingStore.stopRecording()` — it doesn't know or care how recording stops, just that it can.

**`sessionStore`** — Ephemeral, scoped to the recording screen. Tracks `isProcessing`, `processingError`, `failedAudioUri`, and `clarifications`. Resets when the recording screen unmounts. This is pure UI feedback state — "show the spinner," "show the error row," "show the clarification modal."

### Why Not Just Use One?

TanStack Query is purpose-built for server state. It handles caching, deduplication, background refetching, and stale-time management out of the box. Building that from scratch in Zustand would be reinventing the wheel poorly.

Zustand is purpose-built for simple, synchronous, cross-component state. Using TanStack Query for "is the user recording right now?" would be absurd — there's no server to query.

Each tool does what it's best at. The boundary is clean: if the data comes from the server, TanStack Query owns it. If it's UI-only state shared across components, Zustand owns it. Nothing else.

---
