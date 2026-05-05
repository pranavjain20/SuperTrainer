# SuperTrainer — Current Status

_Last updated: 5 May, 2026_

## Current Phase

v1 implementation in progress. Plan creation built (natural language → structured exercises). Live exercise history built. Cleanup pass on nav, voice pipeline, and plan display done.

## Last Session (Apr 17, 2026)

Five root-cause fixes from hands-on phone testing:
- "Back to Home" on ended session was `router.back()`, dropping trainer on client profile instead of home. Switched to `router.replace("/")`.
- Voice pipeline was 404'ing — parser had a hallucinated `claude-sonnet-4-6-20250627` model ID. Fixed to alias `claude-sonnet-4-6`, DRY'd across parser/plan_parser, and added defense-in-depth: `model_health.py` pings `ACTIVE_MODELS` on FastAPI startup (blocks bad deploys) plus a marked `pytest -m smoke` test for explicit CI invocation.
- Plan creation polish: weight field no longer truncates long lists (fixed-width Sets/Reps chips + multiline Weight); new plan now appears on Plans tab after save (swapped `refetchQueries` for `setQueryData` — refetch doesn't reliably match observers across push-nav boundaries); `formatPlanDate` no longer shifts Jan 31 → Jan 30 (UTC-to-local day shift).
- Plan set rendering: parser sometimes emits inconsistent sets counts (sets=6 with 3 weights). Old code silently padded with first value, producing nonsense. New `formatPlannedSets` utility trusts the arrays over sets count, collapses uniform sets to "4 × 10kg×8". 9 unit tests added.
- "Start Over" / "Delete Plan" on the edit form were small text links that looked anemic next to Save Plan. Restyled as proper outlined buttons (side-by-side, `flex: 1`, 1.5px border, Inter-Bold). Matches "buttons big/bold" design preference.

## Blockers

None currently.

## Next Steps

1. Tier 1 #3b — wire plans into session flow (show today's plan on recording screen, auto-link via plan_id). "Back to Home" was the smaller half.
2. Plan modification on the fly (todo #4)
3. End-session plan dictation (todo #5)
4. Settings screen — weight units (todo #6)

## Project Timeline

- **Phase 1a: Backend Foundation** — COMPLETE (306 tests). 10 models, full CRUD, ownership validation, seed data.
- **Phase 1b: Voice Pipeline** — COMPLETE (683 tests). Deepgram STT + Claude parser, 142 exercises, 25/25 live scenarios.
- **Phase 2a: Mobile App** — COMPLETE (734 backend tests, mobile unit tests for formatters, 12 days). Full React Native + Expo app: home, clients, profile, session recording, voice pipeline, inline editing, clarification UX, active session banner.
- **Design System Polish** — COMPLETE (Mar 1). Centralized tokens, ThemedText, Inter + JetBrains Mono, all components migrated.
- **Business Pitch** — COMPLETE (Mar 8). Market data, sourced statistics, trainer-enablement thesis.
- **v1 Scope** — FINALIZED (Apr 3). Notebook replacement + intelligence layer. See tasks/todo.md for full breakdown.
