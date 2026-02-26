# Phase 2 Day 1 — React, React Native, Expo, and Mobile Development

## What React Actually Is

React is one idea: **your UI is a function of your data.** You don't manually update the screen. You describe what the screen should look like for any given state, and React figures out what changed and updates the minimum necessary.

A **component** is a function that takes props (input) and returns JSX (what to render):

```tsx
function Greeting({ name }: { name: string }) {
  return <Text>Hello, {name}!</Text>;
}
```

**State** is data that changes over time. `useState` gives you a value and a setter. When the setter is called, React re-runs the component function with the new value:

```tsx
const [count, setCount] = useState(0);
// setCount(5) → component re-renders with count = 5
```

The core flow: **Props/State change → React re-runs the function → New JSX returned → Screen updates.** That's it. Everything else builds on this.

## React Native: React for Phones

React Native uses the same React model but renders to native platform components instead of HTML:

| HTML (web) | React Native (mobile) | What it is |
|---|---|---|
| `<div>` | `<View>` | Container. Everything is flexbox, defaults to column direction. |
| `<p>`, `<span>` | `<Text>` | Text. ALL text must be inside `<Text>` — no bare strings. |
| `<button>` | `<Pressable>` | Touch target. |
| `<input>` | `<TextInput>` | Text fields. |
| `<ul>` + map | `<FlatList>` | Virtualized list — only renders what's on screen. |

The key difference from web: there's no CSS. Styles are JavaScript objects. `flexDirection` defaults to `column` (vertical), not `row` like web CSS.

## Expo: The Abstraction Over Native

Building a native iOS app normally requires Xcode, a developer account, and a full native build process that takes minutes. Expo removes all of that.

**Three pieces:**
1. **Metro bundler** runs on your laptop. Takes TypeScript files → bundles into JavaScript.
2. **Expo Go** is a pre-built app on your phone. Contains all the native modules (camera, audio, haptics).
3. Your code runs *inside* Expo Go. No native build needed during development.

The flow: `npx expo start` → Metro starts → phone connects over Wi-Fi → downloads JS bundle → app runs. Edit a file → save → phone updates in ~1 second (Fast Refresh). This is why mobile development with Expo feels as fast as web development.

**When you ship:** Expo handles the native build for you (EAS Build). You never touch Xcode unless you need custom native modules.

## File-Based Routing (Expo Router)

Same concept as Next.js: **folder structure IS navigation.**

```
app/
├── _layout.tsx           ← Root layout (wraps everything in providers)
├── (tabs)/
│   ├── _layout.tsx       ← Defines the tab bar
│   ├── index.tsx         ← Home tab (default)
│   ├── brain.tsx         ← Brain tab
│   ├── clients/
│   │   ├── _layout.tsx   ← Stack navigator for clients
│   │   └── index.tsx     ← Client list screen
│   └── session/
│       ├── _layout.tsx   ← Stack navigator for sessions
│       └── index.tsx     ← Session screen
```

**`_layout.tsx`** files don't render screens. They define HOW children render — tabs, stacks, drawers. The root `_layout` says "use a Stack." The `(tabs)/_layout` says "use bottom tabs."

**`(tabs)`** — parentheses mean "layout group." It defines behavior (tabs) without affecting the URL. Home is at `/`, not `/(tabs)/`.

**`[id].tsx`** — brackets mean "dynamic parameter." Like FastAPI's `/{id}`. `useLocalSearchParams()` extracts it.

## NativeWind: Tailwind for React Native

Instead of writing style objects:
```tsx
<View style={{ flex: 1, padding: 16, backgroundColor: '#FAFAFA' }}>
```

You write className strings (like Tailwind on web):
```tsx
<View className="flex-1 p-4 bg-[#FAFAFA]">
```

Same output, but much faster to iterate. The classes are compiled at build time — no runtime overhead.

## TanStack Query: Why We Don't Write useEffect for Fetching

The naive React approach to fetching data:
```tsx
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  fetch('/api/clients').then(res => res.json()).then(setData).catch(setError).finally(() => setLoading(false));
}, []);
```

That's ~10 lines for every fetch. No caching, no refetching, no deduplication.

TanStack Query replaces all of that:
```tsx
const { data, isLoading, isError } = useQuery({
  queryKey: ['clients'],
  queryFn: () => apiGet('/api/v1/clients'),
});
```

It handles: caching (same data isn't re-fetched for 30s), loading/error states, background refetching, pagination, deduplication (two components requesting the same data → one fetch). We'll use this for every API call in the mobile app.

## Zustand: Lightweight State Management

For data that doesn't come from the API — like "is the microphone recording right now?" or "what entries are in the current session?" — we use Zustand. It's a state store in ~5 lines:

```tsx
const useSessionStore = create((set) => ({
  isRecording: false,
  entries: [],
  startRecording: () => set({ isRecording: true }),
  addEntry: (entry) => set(state => ({ entries: [...state.entries, entry] })),
}));
```

No providers, no context wrappers. Import and use anywhere. That's why we picked it over Redux (100x less boilerplate).

## The Architecture Picture

```
Phone (Expo Go)           Laptop (Metro)           Backend (FastAPI)
─────────────────         ────────────────         ──────────────────
                   WiFi                      HTTP
Expo Router  ←──────────→  Metro Bundler
  ↓                         (bundles .tsx)
Tab Navigator
  ↓
Screens (components)
  ↓
TanStack Query  ────────────────────────────────→  /api/v1/...
  ↓                                                    ↓
Zustand (local state)                          PostgreSQL + Services
```

During development, the phone talks to Metro for code updates (Fast Refresh). When the app fetches data, it talks directly to the backend API. These are two separate connections.

## SDK Version vs Expo Go

Expo SDK versions (52, 53, 54, 55...) are like major releases of the platform. Each SDK version bundles specific versions of React, React Native, and Expo packages.

**Expo Go** is a pre-built container app that only supports one SDK at a time (the latest stable). When a new SDK ships (55), it takes time for Expo Go on the App Store to update. During that gap, you either:
- Use the older SDK (what we did — SDK 54 instead of 55)
- Create a "development build" (custom native build that supports any SDK)

For us, SDK 54 vs 55 changes almost nothing. The only difference: we use `expo-av` for audio recording instead of `expo-audio`. Same capability, slightly older API. Easy upgrade path when Expo Go catches up.
