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

## Voice Recording — Five Layers Working Together

The core interaction of the app: trainer taps a button, speaks, and structured data appears on screen. Five layers cooperate to make this feel instant and reliable.

### Layer 1: useVoiceRecorder (expo-av)

Manages the hardware. Requests microphone permission, creates an `Audio.Recording` with high-quality settings (M4A, 44kHz, 128kbps AAC), tracks duration, and returns a local file URI when the trainer stops recording.

Duration tracking uses a wall-clock `setInterval`, not expo-av's status callbacks. Why? The status callbacks fire inconsistently on different devices. A simple `Date.now()` interval is more reliable for showing "0:03... 0:04... 0:05..." on the UI. We don't need millisecond precision — we need consistent ticking.

On mount, the hook registers its `stopRecording` function into `recordingStore`. This is how the tab layout can stop recording without knowing anything about expo-av.

### Layer 2: recordingStore (Zustand)

The bridge between the recording hook and the rest of the app. Components that need to know "is a recording happening?" read from this store. The tab layout reads `isRecording` to guard navigation. The `ActiveSessionBanner` reads `activeClientName` and `activeSessionStartedAt` to show "Recording with Elena — 12:34."

### Layer 3: useVoiceClipUpload

The orchestration hook. When `useVoiceRecorder` produces a URI, this hook:

1. Sets `isProcessing: true` in `sessionStore` (Timeline shows a spinner)
2. Calls `processVoiceClip(sessionId, audioUri)` — multipart POST to the backend
3. Backend runs the full pipeline: Deepgram STT → Claude parser → validation → persistence (~3 seconds)
4. Invalidates the TanStack Query cache for this session's entries (triggers refetch)
5. Clears processing state, surfaces any clarifications

On error, it stores the failed audio URI so the Timeline can show a retry row. The trainer can tap to re-send the same clip without re-recording.

A `useRef` tracks the last uploaded URI to prevent double-uploads. React effects can fire multiple times during re-renders — without this guard, the same clip could be sent to the backend twice.

### Layer 4: sessionStore (Zustand)

Drives the Timeline's feedback UI. Three states:
- `isProcessing: true` → spinner row at the bottom of the timeline
- `processingError` set → error row with retry button
- `clarifications` set → `ClarificationModal` appears

### Layer 5: Timeline Component

Reads session entries from TanStack Query and processing state from `sessionStore`. Renders entry cards (exercise or observation), plus contextual UI rows for processing, errors, and clarifications.

When clarification is needed (the backend couldn't parse the audio), the trainer gets three choices: "Speak Again" (restarts recording), "Type It" (opens `ManualEntryModal` for text input that skips Deepgram and goes straight to Claude), or "Cancel" (dismisses).

### The Full Session Lifecycle

1. Trainer taps "Start Session" on a client profile → `createSession` mutation → navigates to recording screen
2. `recordingStore.setActiveSession` → `ActiveSessionBanner` appears across all tabs
3. Trainer taps the `RecordButton` → button turns red, pulses, haptic feedback fires
4. Trainer taps again → recording stops → URI triggers auto-upload
5. Backend processes (~3 seconds) → cache invalidates → new cards appear on Timeline
6. Trainer can tap any card → edit modal → optimistic cache update (instant UI)
7. Repeat steps 3-6 for each voice clip
8. Trainer taps "End Session" → `ConfirmSheet` → optional `EndTimePickerSheet` → session saved with `ended_at`
9. Screen transitions: Timeline replaced by `SessionSummary` (stats) + "Workout Details" (all entries)
10. Workout classification fires automatically → "Upper Body" / "Lower Body" / "Full Body" label
11. `clearActiveSession` → banner disappears

### Inline Editing — Optimistic Updates

Every entry card is tappable. `ExerciseEditModal` lets the trainer fix exercise names, set data, form notes. `ObservationEditModal` lets them edit observation text and flag colors.

The `useEditableEntries` hook is shared between the recording Timeline and the client profile's session history. It returns both the rendered entry list AND the modal components — the consuming screen just renders both and gets full editing capability for free.

After a mutation, `setQueryData` patches the cached entries array in-place. The UI updates immediately. A background refetch confirms the server accepted the change. If the server rejects it (validation error), the next refetch restores the correct state. This is "optimistic-style" without full rollback machinery — simple enough for our needs, since server rejections are rare for inline edits.

---

## The Design Token System — No Ad-Hoc Values

Every color, font size, font weight, and spacing value in the app comes from one file: `src/constants/tokens.ts`. No hex strings in component files. No inline font sizes. No "what shade of gray was that again?"

### Colors — Semantic, Not Named

Colors aren't named by their hue ("gray-800"). They're named by their purpose:

```typescript
colors.bg.base        // App background
colors.bg.surface1    // Card backgrounds (one layer up)
colors.bg.surface2    // Nested elements (two layers up)
colors.text.primary   // Main text
colors.text.secondary // Supporting text
colors.text.tertiary  // Subtle labels
colors.blue.base      // Primary action color
colors.ai.purple      // AI-generated content (distinct from user content)
colors.recording.red  // Active recording indicator
```

This means components never decide what color to use — they declare what role the color plays. If we rebrand tomorrow and change the primary color from blue to green, one line changes in `tokens.ts` and the entire app updates.

Alpha variants (`colors.blue.alpha12`, `colors.red.alpha12`) are for backgrounds behind colored text — a light tint that provides contrast without visual heaviness.

### Typography — ThemedText as the Gate

`ThemedText` is the only way to render text in the app. It wraps React Native's `<Text>` and applies a variant's full style object:

```tsx
<ThemedText variant="title-1">Session History</ThemedText>
<ThemedText variant="body" color={colors.text.secondary}>No sessions yet</ThemedText>
<ThemedText variant="data-bold">145 kg</ThemedText>
```

13 variants exist, split between two font families:
- **Inter** (Regular/Medium/SemiBold/Bold) — all UI text: titles, body copy, labels, captions
- **JetBrains Mono** (Regular/Bold) — exclusively for data: weights, reps, durations, timers

This split is intentional. Monospaced fonts make numbers align vertically in tables and feel "data-like." Proportional fonts (Inter) are more readable for prose. Using the wrong font for the wrong content type is a subtle but noticeable design flaw.

One gotcha: the `caption` variant includes `textTransform: "uppercase"` baked in. Any text rendered as `caption` will automatically be all-caps. This is by design (column headers, section labels) but surprised us a few times during development.

### Why This Matters

Without a token system, every developer makes independent color and sizing decisions. After 20 components, you have 8 slightly different grays, 3 font sizes that are "close enough," and spacing that looks inconsistent on every screen. The token system makes consistency automatic — you can't use the wrong gray because you never type a hex code.

---

## Quick Reference — Phase 2a Files

### Screens (7 routes)

| File | Screen |
|------|--------|
| `app/(tabs)/index.tsx` | Home — today's sessions |
| `app/(tabs)/clients/index.tsx` | Client list — search, alphabetical grouping |
| `app/(tabs)/clients/[id].tsx` | Client profile — goals, sessions, plans |
| `app/(tabs)/brain.tsx` | Brain — placeholder for Phase 3 |
| `app/(tabs)/session/index.tsx` | All sessions list |
| `app/recording/[sessionId].tsx` | Active recording screen |
| `app/+not-found.tsx` | 404 fallback |

### Components (22)

| Component | Purpose |
|-----------|---------|
| `ThemedText` | Typography gate — all text goes through here |
| `PressableCard` | Base pressable wrapper with card styling |
| `EntryCard` | Routes to ExerciseCard or ObservationCard by type |
| `ExerciseCard` | Set table with data columns (JetBrains Mono) |
| `ObservationCard` | Observation text with flag-color left border |
| `ExerciseEditModal` | Inline exercise editing |
| `ObservationEditModal` | Inline observation editing |
| `ManualEntryModal` | Text input fallback when voice fails |
| `ClarificationModal` | "Speak again" / "Type it" / "Cancel" dialog |
| `ConfirmSheet` | Generic confirm/cancel bottom sheet |
| `EndTimePickerSheet` | Date picker for forgotten end times |
| `RecordButton` | FAB with pulse animation + haptic feedback |
| `ActiveSessionBanner` | Persistent banner across all tabs during recording |
| `Timeline` | Live entry list during recording |
| `SessionHeader` | Recording screen header with end button |
| `SessionSummary` | Post-session stats card |
| `SessionListScreen` | Shared list used by Home and Sessions tabs |
| `SessionRow` | Single row in a session list |
| `ClientRow` | Single row in client list (initials avatar) |
| `EmptyState` | Empty list placeholder |
| `ErrorState` | Error display with retry button |
| `LoadingState` | Loading spinner |

### Hooks (10)

| Hook | Purpose |
|------|---------|
| `useClients` | Client list + `useClientMap` for O(1) lookups |
| `useClient` | Single client, sessions, plans, entries |
| `useSessions` | Today's sessions with client name enrichment |
| `useSession` | Single session fetch |
| `useSessionEntries` | Entries for a given session |
| `useEditableEntries` | Edit modal wiring (shared between screens) |
| `useEntryMutations` | Update + delete entry mutations |
| `useEndSession` | End session + classify workout |
| `useVoiceRecorder` | expo-av recording lifecycle |
| `useVoiceClipUpload` | Upload orchestration |

### Utilities (5 files)

| File | Functions |
|------|-----------|
| `sessions.ts` | `getSessionDisplay`, `computeSessionStats`, `numberExercises`, `classifyWorkoutFromEntries` |
| `sets.ts` | `getSetWeight`, `getSetReps`, `formatCompactSet`, `formatCompactExercise`, `convertWeight` |
| `dates.ts` | `formatTime`, `formatSessionDate`, `formatMemberSince`, `toISODateString` |
| `strings.ts` | `capitalizeFirst`, `capitalizeWords` |
| `initials.ts` | `getInitials`, `getInitialsColor` (deterministic from name) |

### Numbers

- 7 screens, 4 tabs
- 22 components, 10 hooks, 2 Zustand stores
- 13 typography variants, 2 font families (6 font files)
- 734 total tests (701 backend + 33 mobile Jest)
- 12 days of development
