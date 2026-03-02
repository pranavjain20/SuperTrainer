# SuperTrainer Design System

**Read this file in full before creating or modifying any UI component.**

---

## What This App Is

SuperTrainer is an AI voice tool for personal trainers. Trainers tap to speak mid-session — "Jake did 3 sets of squats, 12 reps, 10kg, RPE 6" — and the app transcribes, structures, and logs it in real time. An AI conversational agent (the Brain) answers questions about any client at any time. Pre-session briefings surface injury patterns and preparation context.

The target user is a 35-50 year old independent trainer or Equinox-caliber gym trainer with 20-40 active clients. They charge $100-150/session. They are not technical. They use this app mid-session with a client standing in front of them. They glance at it for 2-3 seconds. They tap once. They speak. They move on.

**The design must feel like:** A serious professional intelligence tool that gives an unfair advantage. Think Bloomberg terminal meets Whoop. Not a consumer fitness app. Not a prototype. Not a logging tool.

---

## Design Philosophy

### 1. Command Center, Not Consumer App

This is closer to Linear or Bloomberg than to MyFitnessPal. Information density over decoration. Dark surfaces that reduce glare in gym lighting. No rounded-pastel-gradient energy. No illustrations. No emoji. A trainer's command center.

### 2. Glanceability Is Everything

The trainer looks at the phone for 2-3 seconds between sets. In that time they must confirm: the right exercise was logged, the right weight and reps appeared, nothing is flagged red. Typographic hierarchy does 80% of the work. Color is semantic, never decorative. Numbers are sacred — they use monospace so columns align perfectly for vertical scanning.

### 3. Earned Intelligence

The AI never overstates what the data supports. This epistemic honesty is expressed visually: AI-generated content looks distinctly different from trainer-logged data. The trainer always knows at a glance: "this is what I said" vs "this is what the machine inferred." Confidence is communicated through visual weight — low-data insights look more tentative than high-confidence patterns.

### 4. One-Handed, Mid-Session

The trainer holds the phone in one hand. Primary actions live at the bottom. The mic button is the largest tap target in the app. Minimum tap targets: 48pt everywhere, 80pt for the mic button. Vertical scroll only — no horizontal carousels or swipe-to-reveal.

---

## Color System

### Background: Blue-Tinted Dark

Blue-tinted dark backgrounds look more sophisticated on digital screens than neutral grey because LCD/OLED panels emit slight blue light that harmonizes with blue-tinted surfaces. This is the approach used by Linear, GitHub Dark, and Twitter/X Dim mode. It reads as more premium than Material Design's neutral #121212.

```
BACKGROUNDS — Depth stack (lighter = higher elevation)
──────────────────────────────────────────────────────
bg-base:            #0F172A     App canvas. Behind everything.
bg-surface-1:       #1E293B     Primary cards — exercise cards, client rows, session cards.
bg-surface-2:       #334155     Elevated surfaces — modals, active session header, focused inputs.
bg-surface-3:       #475569     Highest elevation — tooltips, popovers.

Each step is ~5% lighter than the previous. This creates depth without shadows.
Shadows are invisible on dark backgrounds. Never use them except on the mic button.
```

```
TEXT — Never use pure white. Cap at #F1F5F9.
──────────────────────────────────────────────
Pure white on dark backgrounds causes halation — visual blooming that strains
eyes during long training sessions. Superhuman's design team documented this.
Use 90% opacity white equivalent instead.

text-primary:       #F1F5F9     Headings, exercise names, weight values, rep counts.
text-secondary:     #94A3B8     Labels, column headers (SET/REPS/WEIGHT), timestamps, metadata.
text-tertiary:      #64748B     Placeholders, disabled states, "previous workout" ghost data.
text-inverse:       #0F172A     Text on colored backgrounds (buttons, badges).
```

```
PRIMARY ACCENT — Sky Blue
─────────────────────────
Used for: buttons, links, active tab indicator, interactive elements. Nothing else.

blue-500:           #38BDF8     Primary interactive color.
blue-600:           #0EA5E9     Pressed/active state.
blue-400:           #7DD3FC     Light variant — selected states, active timer text.
blue-900:           #0C4A6E     Subtle background tint for blue-context areas.
blue-alpha-12:      rgba(56, 189, 248, 0.12)    Badge and tag backgrounds.
```

```
AI ACCENT — Purple-to-Blue
──────────────────────────
This color family ONLY appears on AI-generated content.
Never on trainer-entered data. Never on UI chrome.
This distinction must be immediately visible at a glance.

ai-500:             #8B5CF6     AI accent — observation card borders, AI badge text.
ai-400:             #A78BFA     AI accent light — insight highlights.
ai-900:             #1E1338     AI content background tint.
ai-alpha-10:        rgba(139, 92, 246, 0.10)    Subtle AI background fill.

WHY PURPLE: Canva, Notion AI, Microsoft Designer, Whimsical, and Framer
all use purple for AI features. Users now associate purple with AI-generated
content. Teal was considered but purple has stronger learned association.
```

```
SEMANTIC — Status colors (desaturated ~20% vs light mode equivalents)
─────────────────────────────────────────────────────────────────────
Saturated colors vibrate against dark backgrounds. Desaturate all accents.

green-500:          #22C55E     Positive flags, completed sets, PRs, good status.
green-900:          #14332A     Green tint background.
green-alpha-12:     rgba(34, 197, 94, 0.12)

amber-500:          #F59E0B     Warning, caution flags, warm-up sets, in-progress states.
amber-900:          #332B14     Amber tint background.
amber-alpha-12:     rgba(245, 158, 11, 0.12)

orange-500:         #F97316     Recurring concern flags.
orange-900:         #331E11     Orange tint background.
orange-alpha-12:    rgba(249, 115, 22, 0.12)

red-500:            #EF4444     Danger, pain flags, significant concerns, recording state.
red-900:            #331616     Red tint background.
red-alpha-12:       rgba(239, 68, 68, 0.12)
```

```
RECORDING STATE
───────────────
recording-red:      #EF4444     Mic button when actively recording. Universal convention.
recording-glow:     rgba(239, 68, 68, 0.25)    Pulsing glow around mic during recording.
```

```
BORDERS
───────
border-subtle:      #334155     Card edges, row dividers. Matches surface-2 for clean stepping.
border-default:     #475569     Input field borders. More visible.
border-strong:      #64748B     Focused input borders.
```

### Color Usage Rules — Non-Negotiable

1. **`ai-*` colors are EXCLUSIVELY for AI-generated content.** Observations, insights, briefings, pattern flags, brain responses. If a trainer logged it directly, it never touches purple.
2. **Flag colors match the four-level system:** Green (positive), Amber (minor concern), Orange (recurring concern), Red (significant concern).
3. **Blue is interactive.** Buttons, links, active tab, Start Session CTA. Never for status or content.
4. **No color without semantic meaning.** If you cannot name its purpose, use `text-secondary` or `border-subtle`.
5. **Never use pure white (#FFFFFF) for text.** Maximum is `text-primary` (#F1F5F9).

---

## Typography

### Font Choices

**Body text: Inter.** Designed for screens. Supports tabular-lining numerals. Same font Linear uses. Available via `@expo-google-fonts/inter`. Load weights 400 (Regular), 500 (Medium), 600 (SemiBold), 700 (Bold).

**Numeric data: JetBrains Mono.** For weights, reps, sets, RPE, timers — anywhere numbers appear in data tables or counters. Monospace ensures equal-width digits so columns align perfectly for vertical scanning. This is the single most impactful decision for making workout tables feel designed rather than spreadsheet-like. Load weights 400 (Regular), 700 (Bold).

Load both via Expo config plugin:
```json
{
  "plugins": [
    ["expo-font", {
      "fonts": [
        "./assets/fonts/Inter-Regular.ttf",
        "./assets/fonts/Inter-Medium.ttf",
        "./assets/fonts/Inter-SemiBold.ttf",
        "./assets/fonts/Inter-Bold.ttf",
        "./assets/fonts/JetBrainsMono-Regular.ttf",
        "./assets/fonts/JetBrainsMono-Bold.ttf"
      ]
    }]
  ]
}
```

### Type Scale

```
display:        Inter-Bold,         34px,   lineHeight: 42    Screen titles (Today, Clients, Brain)
title-1:        Inter-Bold,         24px,   lineHeight: 30    Client names on profiles
title-2:        Inter-SemiBold,     20px,   lineHeight: 28    Exercise names in session timeline
title-3:        Inter-SemiBold,     16px,   lineHeight: 22    Subsection headings, plan titles
body:           Inter-Regular,      16px,   lineHeight: 24    Readable text, observations, brain responses
body-medium:    Inter-Medium,       16px,   lineHeight: 24    Slightly emphasized body text
body-small:     Inter-Regular,      14px,   lineHeight: 20    Secondary descriptions
caption:        Inter-Medium,       12px,   lineHeight: 16    Column headers, status labels
                                    letterSpacing: 0.8, textTransform: uppercase

data:           JetBrainsMono-Regular, 16px, lineHeight: 24   Numbers in exercise tables
data-bold:      JetBrainsMono-Bold,    16px, lineHeight: 24   Highlighted numbers (PRs, key values)
data-large:     JetBrainsMono-Bold,    28px, lineHeight: 34   Hero stat numbers (client score, timer)
timer:          JetBrainsMono-Regular,  48px, lineHeight: 56   Session timer display

small:          Inter-Regular,      13px,   lineHeight: 18    Fine print, "Training since Jan 2026"
```

### Typography Rules

1. **Exercise names are always `title-2` (20px, SemiBold).** Primary anchor in any session timeline.
2. **Column headers (SET, REPS, WEIGHT, RPE) are always `caption` — 12px, Medium, uppercase, letter-spaced.**
3. **All numeric data in tables uses JetBrains Mono.** Non-negotiable.
4. **Dark mode requires heavier weights.** Body text 400 minimum, never 300/Light.
5. **All-caps reserved exclusively for `caption`** — column headers, status labels.

---

## Spacing System

### Base Unit: 8px (with 4px sub-grid)

```
space-0.5:   4       Tightest — icon to label gap
space-1:     8       Between tightly related elements — set rows
space-1.5:   12      Standard compact padding — tags, small badges
space-2:     16      Standard content padding — card internal padding
space-3:     24      Between sections within a card, between cards in a list
space-4:     32      Large section gaps — header to content
space-5:     40      Major section dividers
space-6:     48      Screen-level top padding
```

### Key Dimensions

```
Card border-radius:     12
Input border-radius:    8
Badge border-radius:    24
Exercise card gap:      12
Set row height:         48-52dp
Tab bar height:         56 + safeAreaBottom
Screen horizontal pad:  20
Card internal padding:  16
```

---

## Component Specifications

### Cards

```
Base card:
  backgroundColor: bg-surface-1 (#1E293B)
  borderRadius: 12
  borderWidth: 1
  borderColor: border-subtle (#334155)
  padding: 16
  marginBottom: 12

AI card (observations, insights):
  backgroundColor: ai-alpha-10
  borderLeftWidth: 3
  borderLeftColor: ai-500 (#8B5CF6)
  borderRadius: 12
  borderWidth: 1 (other sides), borderColor: border-subtle
```

No drop shadows on cards. Depth from color stepping + borders.

### The Exercise Data Table

Follows the Hevy/Strong gold standard — the most successful workout logging UI pattern.

```
┌───────────────────────────────────────────────────┐
│  ● 1    Goblet Squat                          ✏️  │
│                                                    │
│  SET    PREVIOUS     KG       REPS    RPE          │
│   1     10kg × 10    10       10       6           │
│   2     10kg × 10    10       10       6           │
│   3     10kg × 10    10       10       6           │
└───────────────────────────────────────────────────┘
```

- **Exercise number badge:** 24pt circle, blue-500 bg, white Inter-Bold 14px
- **Exercise name:** title-2 (Inter-SemiBold 20px), text-primary
- **Column headers:** caption (Inter-Medium 12px, uppercase), text-secondary
- **PREVIOUS column:** Shows last session data "10kg × 10" in text-tertiary. THE most valued UX feature in top workout apps. If no previous, show "—"
- **Data cells:** JetBrains Mono Regular 16px, text-primary
- **Empty cells:** em-dash "—" in text-tertiary. Never blank. Never zero.
- **Set number:** text-secondary. Tappable for set type (Normal/Warm-up/Drop/Failure)
- **Row dividers:** 1px border-subtle between rows
- **Column widths:** SET: 40, PREVIOUS: flex 1, KG: 60, REPS: 60, RPE: 50 (hide if unused)

### Observation & AI Cards

```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│ ✦ AI INSIGHT                                  ✏️  │
│                                                    │
│ Progressed goblet squat to 10kg —                  │
│ handled it well. Confidence growing.               │
│                                                    │
│ Based on 8 sessions                                │
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

- 3px left border in ai-500 (purple). Primary AI visual signal.
- Background: ai-alpha-10
- Sparkle icon ✦ + label in caption style, ai-500 color
- Content: body style, text-primary
- Attribution: "Based on 8 sessions" in small style, text-tertiary

Flag severity modifies border/label color: amber (minor), orange (recurring), red (significant), green (positive).

### Buttons

```
Primary:     blue-500 bg, text-inverse, borderRadius 12, paddingV 16, paddingH 24, full width
Secondary:   transparent bg, border-default border 1.5px, text-primary, borderRadius 12
Destructive: red-500 bg, white text, same dimensions as primary
Ghost:       transparent, no border, blue-500 text
```

### Bottom Tab Bar

```
bg: bg-surface-1, borderTop: 1px border-subtle, height: 56 + safe area
Tabs: Home, Clients, Brain, Sessions
Active: blue-500, Inactive: text-tertiary
Brain icon: lightning bolt (NOT chat bubble)
```

### Active Session Bar (above tab bar, visible on all tabs during session)

```
bg: blue-500, borderRadius 14 top, paddingV 14, paddingH 20
Left: green pulse dot + client name (Inter-SemiBold 16px white)
Right: timer (JetBrains Mono 16px white) + chevron
```

---

## The Microphone Button

80pt minimum. Sweaty hands in a gym need a big target.

```
Resting:    72x72, borderRadius 36, blue-500, mic icon 28pt white
            Shadow: blue-500, opacity 0.25, radius 16 (ONLY shadow in app)
            Position: absolute, bottom-right, above session bar

Recording:  88x88, borderRadius 44, red (#EF4444), stop icon 28pt white
            Pulsing glow: shadow radius 16↔32, opacity 0.2↔0.4, 1200ms loop
            Spring animation on size change, 200ms

Haptics: Medium impact on start, Light impact on stop
```

---

## The Brain Interface

```
User messages:  right-aligned, blue-alpha-12 bubble, borderRadius 16
AI responses:   left-aligned, no bubble, sparkle ✦ avatar in ai-500
                Stream character-by-character with blinking cursor
Follow-up chips: bg-surface-2, border-subtle, borderRadius 20, Inter-Medium 14px

Three honest states:
1. Full answer:    normal response
2. Partial answer: amber info bar "⚠ Limited data — only 2 sessions"
3. Looking it up:  searching indicator → answer with source
```

---

## Motion

```
New card appearing:        slide up 16px + fade in, 200ms, ease-out
Mic rest → recording:      scale 1→1.22, 200ms spring
Recording → rest:          scale 1.22→1, 150ms ease-out
Recording glow:            shadow pulse, 1200ms loop
Set logged confirmation:   green tint flash, 500ms fade
AI text:                   character-by-character streaming
```

No animation on: tab switches, data value changes, empty states, session bar.

---

## Anti-Patterns — Banned

1. No skeleton screens
2. No illustration empty states
3. No gradients on backgrounds/cards
4. No shadows on cards (only mic button)
5. No pill buttons (max borderRadius: 12)
6. No emoji
7. No decorative color
8. No horizontal carousels
9. No success toasts (errors only)
10. No confirm dialogs for reversible actions
11. No pure white (#FFFFFF) text
12. No hardcoded hex in component files

---

## Implementation

### Tokens (tokens.ts)

```typescript
export const colors = {
  bg: { base: '#0F172A', surface1: '#1E293B', surface2: '#334155', surface3: '#475569' },
  text: { primary: '#F1F5F9', secondary: '#94A3B8', tertiary: '#64748B', inverse: '#0F172A' },
  blue: { 500: '#38BDF8', 600: '#0EA5E9', 400: '#7DD3FC', 900: '#0C4A6E', alpha12: 'rgba(56,189,248,0.12)' },
  ai: { 500: '#8B5CF6', 400: '#A78BFA', 900: '#1E1338', alpha10: 'rgba(139,92,246,0.10)' },
  green: { 500: '#22C55E', 900: '#14332A', alpha12: 'rgba(34,197,94,0.12)' },
  amber: { 500: '#F59E0B', 900: '#332B14', alpha12: 'rgba(245,158,11,0.12)' },
  orange: { 500: '#F97316', 900: '#331E11', alpha12: 'rgba(249,115,22,0.12)' },
  red: { 500: '#EF4444', 900: '#331616', alpha12: 'rgba(239,68,68,0.12)' },
  recording: { red: '#EF4444', glow: 'rgba(239,68,68,0.25)' },
  border: { subtle: '#334155', default: '#475569', strong: '#64748B' },
} as const;

export const spacing = {
  xs: 4, sm: 8, md: 12, base: 16, lg: 24, xl: 32, '2xl': 40, '3xl': 48,
} as const;

export const radii = { sm: 8, base: 12, lg: 16, pill: 24, full: 9999 } as const;
```

### Required Libraries

- `react-native-reanimated` — animations
- `expo-haptics` — haptic feedback
- `react-native-safe-area-context` — safe areas
- `@expo/vector-icons` (Ionicons) — icons
- `expo-font` — Inter + JetBrains Mono

### Critical Rules

1. Every screen root: `bg-base` (#0F172A). No white flash.
2. StatusBar: `light-content` globally.
3. ScrollView bottom padding: 140+ (mic + session bar + tab bar).
4. Active session bar in root layout, not individual screens.
5. All colors from tokens import. Zero hardcoded hex.
6. All Text uses themed wrapper with variant prop.

### Checklist

- [ ] Background #0F172A
- [ ] StatusBar light-content
- [ ] Colors from tokens only
- [ ] Text variant system
- [ ] Numbers in JetBrains Mono
- [ ] PREVIOUS column in exercise tables
- [ ] AI content: purple border + tint + sparkle
- [ ] Trainer data never purple
- [ ] Four-level flag colors
- [ ] Tap targets 48pt+, mic 72pt+
- [ ] Bottom padding 140pt+
- [ ] No shadows except mic
- [ ] No skeletons/emoji/illustrations/gradients
- [ ] Safe area insets
- [ ] Haptics on mic
