# F1 Oracle — Visual Design Brief

> **For Claude Design:** This brief describes a real, working web application that needs a visual redesign. Generate high-fidelity mockups for all three pages. The app is built in Next.js with Tailwind CSS. All component structure and data shapes are real.

---

## What This App Does

**F1 Oracle** is a public scorecard that runs an ML model against Formula 1 prediction markets on [Kalshi](https://kalshi.com). After each race, the model's predictions are graded. Visitors can see:

- The Oracle's probability estimates vs. what the Kalshi crowd thinks
- A virtual $1,000 portfolio growing or shrinking based on those bets
- A season-long win/loss record

**Core question the app answers:** *Does having an ML model beat following the crowd on F1 markets?*

No real money. No user accounts. Read-only public scorecard.

---

## Visual Direction

**Reference inspiration:** The attached dashboard screenshot — premium dark SaaS analytics product. Specifically:
- Near-black background (`#0A0A0A` / `#0D0D0D`)
- Cards with subtle borders and layered dark backgrounds (not flat, not glassy)
- Clean data tables with proper row contrast
- Bold headline numbers with supporting labels
- Area/line charts for time-series data
- Tight, confident typography — no decorative elements

**F1 Oracle's accent palette:**
- **Primary accent:** F1 Red `#E8002D` — used for Oracle probability bars, active tab indicators, the wordmark
- **Win/profit:** Emerald green `#34D399` — all positive P&L, winning bets, upward returns
- **Loss/negative:** Red `#F87171` — negative P&L (lighter than F1 red to distinguish)
- **Kalshi prices:** `#71717A` (zinc-500) — secondary data, lower visual weight than Oracle
- **BET indicator:** Emerald `#10B981` with `rgba(16,185,129,0.15)` background — rows where Oracle placed a virtual bet

**Typography:** Geist Sans for UI, Geist Mono for numbers and percentages (tabular-nums, aligned columns)

**Do NOT use:** gradients on cards, glow effects, glassmorphism, F1 helmet icons, checkered flag patterns, racing stripe decorations. Keep it data-forward and analytical, not sports-themed.

---

## Layout

**Shell structure:**
```
┌─────────────────────────────────────────────────────┐
│ HEADER: F1 Oracle wordmark + tagline                │
├─────────────────────────────────────────────────────┤
│ TAB NAV: Race Weekend | Season Record | Portfolio   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  MAIN CONTENT (max-width ~1100px, centered)        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Header:** Left-aligned logo. `F1` in F1 Red bold, `Oracle` in white semibold. Subtitle: `ML model vs the crowd` in muted zinc. No avatar, no search, no notifications — this is public/read-only.

**Tab nav:** Underline-style tabs flush below the header. Active tab: white text + F1 Red bottom border. Inactive: zinc-400, no border.

---

## Page 1: Race Weekend

> Shows the Oracle's current race predictions vs. Kalshi market prices, with sub-market tabs.

### Top area
- Race name as page title (e.g., `Miami Grand Prix 2026`)
- Subtitle: `Round 4 · Miami · Model updated May 2, 9:14 PM`
- Summary strip when bets exist: `Oracle placed 3 bets on this market (edge ≥ 5%)`

### Market tabs
Pill-style toggle row (not page-level tabs): `Race Winner` | `Podium` | `Pole Position`
Active pill: F1 Red filled. Inactive: dark zinc filled, zinc-400 text.

### Predictions table
Full-width card with subtle border. One row per driver, sorted by Oracle probability descending.

**Columns:**
| # | Driver | Oracle vs Kalshi | Edge |
|---|--------|-----------------|------|

- **#** — rank number, small zinc-600
- **Driver** — `ANT` in monospace bold white, `Andrea Kimi Antonelli` in zinc-400 small. If Oracle placed a bet on this row, show a small `BET` pill (emerald background, emerald text)
- **Oracle vs Kalshi** — stacked mini probability bars:
  - Row 1: F1 Red bar, `46.8%` in white
  - Row 2: zinc bar, `39.0%` in zinc-500 (Kalshi mid-price; hidden if market is illiquid/>94%)
  - Bar track width: ~80px, height: 6px, rounded
- **Edge** — `▲ 7.8%` in emerald if positive, `▼ 2.1%` in red if negative, `—` in zinc-600 if <2%

**Row backgrounds:**
- Rows with a BET: very subtle emerald tint — `rgba(16,185,129,0.08)` — left border accent 2px emerald
- Normal rows: `#111111` / `#0D0D0D` alternating or a single flat dark
- Hover: subtle lightening

### Table header
`text-xs uppercase tracking-widest zinc-500` — minimal, not heavy

### Legend
Small row below the table:
- `●` F1 Red dot — Oracle probability
- `●` zinc dot — Kalshi mid-price
- `BET` pill — Virtual bet placed (edge ≥ 5%)

---

## Page 2: Season Record

> The Oracle's historical win/loss record across past races, with expandable race detail.

### Summary stats strip (top)
Three stat cards in a row:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Bets         │  │ Hit Rate     │  │ Virtual P&L  │
│ 47           │  │ 61%          │  │ +$142.33     │
└──────────────┘  └──────────────┘  └──────────────┘
```

- Card: dark background, 1px zinc-800 border, subtle inner shadow
- Label: `text-xs uppercase zinc-500`
- Value: `text-3xl font-bold` — white for neutral, emerald for positive P&L, red for negative
- P&L shows `+` prefix when positive

### Race accordion list
Each past race is a collapsible row. Default: most recent race expanded.

**Collapsed row (header):**
```
R4  Miami Grand Prix   May 3, 2026     6/8    +$58.20   ▼
```
- `R4` — round badge, zinc-600 monospace
- Race name — white semibold
- Date — zinc-500 small
- `6/8` — wins/total bets, zinc-400
- P&L — emerald or red, monospace
- Chevron — right-aligned

Header background: zinc-900. Hover: zinc-800. Expand/collapse on click.

**Expanded detail (table inside the card):**

Columns: `Driver | Market | Oracle | Kalshi | Edge | Bet Size | Result | P&L`

- Driver: white
- Market: `WIN` / `PODIUM` / `POLE` badge — small pill, zinc-700 background, zinc-300 text
- Oracle %: white monospace
- Kalshi %: zinc-500 monospace
- Edge: emerald `+7.8%`
- Bet size: `$24.50` zinc-300
- Result: `WIN ✓` emerald or `LOSS ✗` red
- P&L: emerald or red, monospace, `+$18.22` / `-$24.50`

Table background: slightly darker than the header — `#0A0A0A`

---

## Page 3: Portfolio

> Virtual $1,000 portfolio performance over time vs. a Kalshi average baseline.

### Stat cards row (top)
Four cards across:

```
┌─────────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐
│ Portfolio Value │  │ Oracle   │  │ Kalshi Avg   │  │ Races     │
│ $1,142.33       │  │ Return   │  │ Return       │  │ Played    │
│                 │  │ +14.23%  │  │ +3.80%       │  │ 4         │
└─────────────────┘  └──────────┘  └──────────────┘  └───────────┘
```

- First card (Portfolio Value) is double-width on mobile, normal on desktop
- Return percentages: large, emerald if positive, red if negative
- Cards: same dark card style as Season Record

### Portfolio chart
Full-width card. Line chart showing two series over time (x-axis = race number/name):

- **Oracle portfolio** — F1 Red line, slightly thicker, labeled
- **Kalshi average baseline** — zinc-500 dashed line, labeled
- Both lines start at `$1,000`
- Y-axis: dollar values
- X-axis: race names/rounds
- Tooltip on hover: show both values + the race name
- Chart background: `#0A0A0A`
- Grid lines: very subtle zinc-800

### History table
Below the chart. Each row = one settled race.

Columns: `Race | Oracle Portfolio | Oracle Return | Kalshi Avg`

- Race: white
- Portfolio value: white monospace `$1,142.33`
- Return: emerald `+5.8%` or red `-2.1%` (this race's single-race return, not cumulative)
- Kalshi avg: zinc-500 `$1,038.00`

Sorted most-recent-first.

---

## Component Inventory

### Stat Card
```
┌────────────────────────────┐
│ LABEL (xs, uppercase)      │
│ VALUE (2xl-3xl, bold)      │
└────────────────────────────┘
```
- Border: 1px `#27272A` (zinc-800)
- Background: `#18181B` (zinc-900)
- Padding: 16px
- Border radius: 8px

### Data Table
- Container border: 1px zinc-800, border-radius 8px, overflow hidden
- Header: zinc-900 background, xs uppercase zinc-500 text
- Rows: zinc-950 background
- Dividers: 1px zinc-800
- Hover: zinc-900

### Pill/Badge
- Active market tab: F1 Red `#E8002D` background, white text
- Inactive market tab: `#27272A` background, zinc-400 text
- BET badge: `rgba(16,185,129,0.15)` background, `#34D399` text, 1px emerald border
- Market type badge (WIN/PODIUM/POLE): `#27272A` background, zinc-300 text

### Probability Bar
```
[████░░░░░░] 46.8%   ← Oracle (F1 Red)
[███░░░░░░░] 39.0%   ← Kalshi (zinc-500)
```
- Track: zinc-800, 80px wide, 6px tall, rounded
- Fill: color per series
- Label: xs monospace, 40px width, right-aligned

### Edge Badge
- `▲ 7.8%` — emerald, xs, semibold
- `▼ 2.1%` — red, xs, semibold
- `—` — zinc-600, xs

---

## States to Show

### Race Weekend — no predictions yet
Empty state card: `No predictions yet for this market. Run the model after qualifying.`
Centered, zinc-500, inside a bordered card.

### Season Record — no settled races
`No settled bets yet. Season record will appear here after the first race.`

### Portfolio — first race pending
`Portfolio history will appear here after the first settled race.`

---

## What NOT to Include in Mockups

- No login / account UI
- No "place a real bet" CTAs or Kalshi branding beyond data attribution
- No mobile navigation drawer — this is primarily desktop/tablet
- No dark mode toggle (always dark)
- No loading skeletons (data is server-rendered)
- No search or filter controls on any page (not in scope)

---

## Data Examples for Mockups

Use these real values so the mockup feels authentic:

**Race Weekend (Miami GP 2026, Race Winner market):**
| # | Abbrev | Driver | Oracle | Kalshi | Edge |
|---|--------|--------|--------|--------|------|
| 1 | ANT | Andrea Kimi Antonelli | 46.8% | 39.0% | ▲7.8% BET |
| 2 | NOR | Lando Norris | 22.1% | 28.0% | ▼5.9% |
| 3 | VER | Max Verstappen | 18.4% | 19.0% | ▼0.6% |
| 4 | LEC | Charles Leclerc | 6.2% | 7.0% | ▼0.8% |
| 5 | PIA | Oscar Piastri | 4.1% | 4.0% | ▲0.1% |

**Portfolio stats:**
- Portfolio Value: $1,058.20
- Oracle Return: +5.82%
- Kalshi Avg Return: +1.40%
- Races Played: 4

---

## Tech Notes (for implementation reference, not design)

- Next.js 16 App Router with React Server Components
- Tailwind CSS v4
- Recharts 3 for the portfolio chart
- Fonts: Geist Sans + Geist Mono (already loaded via `next/font/google`)
- Target: Vercel deployment, public read-only

---

*Brief prepared May 2026 for F1 Oracle redesign. All data is real from shadow mode operation.*
