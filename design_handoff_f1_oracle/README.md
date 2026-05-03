# Handoff: F1 Oracle — Three-Page Redesign

## Overview

F1 Oracle is a public, read-only scorecard that runs an ML model against Formula 1 prediction markets on Kalshi. After each race the model's predictions are graded; visitors can see the Oracle's probability estimates vs. the Kalshi crowd, a virtual $1,000 portfolio's performance, and a season-long win/loss record.

This bundle contains high-fidelity design references for the three pages: **Race Weekend**, **Season Record**, and **Portfolio**.

## About the Design Files

The files in this bundle are **design references created in HTML** — interactive prototypes showing intended look and behavior, not production code to copy directly. The task is to **recreate these designs in the F1 Oracle codebase** (Next.js 16 App Router + React Server Components + Tailwind CSS v4 + Recharts 3, per the design brief) using its established patterns. The HTML uses inline styles via React for prototyping speed; the production version should use Tailwind utilities and proper RSC component decomposition.

Each "page" component in the prototype maps to one route's main view. The shared `Shell` becomes a layout. Tab navigation should be real Next.js `<Link>` components.

## Fidelity

**High-fidelity.** All colors, typography, spacing, and component anatomy are final and should be matched precisely. The included Tweaks panel exposes design alternatives (accent color, background tone, density, card style) — the **chosen final values** are listed in *Design Tokens* below; treat the other tweak options as exploratory and ignore them in production.

## Final Design Decisions

After review, the following Tweak settings are the agreed-upon production values:

| Token       | Value      | Notes                              |
|-------------|------------|------------------------------------|
| Background  | `#100D0B`  | "Warm Black" — slightly warm tint  |
| Accent      | `#E8002D`  | F1 Red — wordmark + active states  |
| Density     | regular    | 14–16px row padding                |
| Card style  | bordered   | 1px zinc-800 border, no shadow     |
| Mono stats  | on         | Geist Mono for stat-card numbers   |
| BET highlight | on       | Emerald tint + left border on bet rows |

## Pages

### 1. Race Weekend (`/`)

**Purpose:** Show the Oracle's current-race predictions vs. Kalshi market prices, with sub-market tabs.

**Layout (top → bottom):**
- Page title `Miami Grand Prix 2026` (32px, weight 600, letter-spacing -0.025em) with right-aligned status `LIVE · MODEL v0.4.2` (12px Geist Mono, color `#52525B`)
- Subtitle `Round 4 · Miami International Autodrome · Model updated May 2, 9:14 PM` (13px, `#71717A`)
- Bet summary strip: emerald-tinted card (`rgba(16,185,129,0.06)` bg, `rgba(16,185,129,0.25)` border) containing a `BET` badge and the message `Oracle placed 3 bets on this market — total stake $73.50 (edge ≥ 5%)`
- Market tabs: pill row, `Race Winner | Podium | Pole Position`. Active = F1 Red filled, white text. Inactive = `#18181B` bg, `#A1A1AA` text, `#27272A` border.
- Predictions table inside a `SectionCard`. Columns: `# | Driver | Oracle vs Kalshi | Edge`.
  - Rank: `01`–`08`, monospace 12px, `#52525B`
  - Driver cell: `ABBR` (monospace bold 13px, white) + full name (13px, `#A1A1AA`) + optional `BET` badge
  - Oracle vs Kalshi: stacked dual probability bars — F1 Red over zinc-500, 90px wide, 6px tall track, with right-aligned `46.8%` mono labels
  - Edge: `▲ 7.8%` emerald (`#34D399`) if ≥ 2%, `▼ 2.1%` red (`#F87171`) if ≤ −2%, `—` (`#52525B`) otherwise
  - Bet rows: `rgba(16,185,129,0.06)` bg, 2px `#10B981` left border. Non-bet rows alternate `#0A0A0A` / `#0C0C0E`.
- Legend below table: red dot Oracle / zinc dot Kalshi / `BET` badge legend

**Data source:** `Race Winner` market for Miami GP 2026. 8 drivers (Antonelli, Norris, Verstappen, Leclerc, Piastri, Russell, Hamilton, Sainz). Antonelli row is the only `BET` in the visible mockup.

### 2. Season Record (`/season`)

**Purpose:** The Oracle's historical win/loss record across past races, with expandable race detail.

**Layout:**
- H1 `Season Record` + subtitle `2026 season · 4 of 24 races settled`
- Three stat cards in a row: `Bets / 47`, `Hit Rate / 61%`, `Virtual P&L / +$110.90` (emerald)
- Race accordion list — one card per race. Default: most recent (Miami) expanded.
  - Collapsed header grid: `R4 | Miami Grand Prix | May 3, 2026 | 6/8 | +$58.20 | ▾`
  - Header bg toggles `#0E0E10` (collapsed) / `#131316` (expanded)
  - P&L colored emerald or red, monospace, with `+`/`−` prefix and 2-decimal precision
- Expanded detail: nested table on `#08080A` bg. Columns: `Driver | Market | Oracle | Kalshi | Edge | Bet Size | Result | P&L`.
  - Market column uses `WIN` / `PODIUM` / `POLE` pill (`#27272A` bg, `#D4D4D8` text, monospace 10px)
  - Result column: `WIN ✓` emerald or `LOSS ✗` red

### 3. Portfolio (`/portfolio`)

**Purpose:** Virtual $1,000 portfolio performance over time vs. a Kalshi-average baseline.

**Layout:**
- H1 `Portfolio` + subtitle `Virtual $1,000 starting bankroll · Kelly-fractional sizing · No real money`
- Four stat cards: `Portfolio Value $1,142.33` / `Oracle Return +14.23%` (emerald) / `Kalshi Avg Return +3.80%` / `Races Played 4`
- Chart card (full-width):
  - Header row: title `Cumulative performance` + sub `$ value across the 2026 season`. Right side: legend with current values (Oracle $1,142.33, Kalshi avg $1,038.00).
  - SVG line chart. X axis: `Start, Bahrain, Saudi, Japan, Miami`. Y axis: `$1,000–$1,150`, 4 ticks. Oracle line: 2px solid F1 Red with subtle red gradient area fill (18% → 0% opacity). Kalshi line: 1.5px dashed `#71717A`. Points on every Oracle data point; final point larger with a stroke matching page bg.
  - Tooltip pinned to the latest point: `MIAMI · R4`, `Oracle $1,142.33`, `Kalshi $1,038.00` in a `#131316` rounded box with `#27272A` border
- History table below: `Race | Oracle Portfolio | Race Return | Kalshi Avg`, sorted most-recent first. Race Return colored emerald/red.

**For production:** use **Recharts 3** for the chart (per the brief), not the custom SVG in the prototype. The visual treatment to match: red `Line` with a `defs`-defined linear gradient `Area` fill, and a dashed gray `Line` for the baseline.

## Shared Shell

Every page renders inside a common shell:

- **Header:** centered max-width 1100px container, 32px top padding. Wordmark = `F1` (weight 800, `#E8002D`, 26px) + `Oracle` (weight 600, white, 26px), then 14px gap, then `ML model vs the crowd` (13px, `#52525B`).
- **Tab nav:** flush below header, 1px `#1F1F23` bottom border. Three tabs: `Race Weekend | Season Record | Portfolio`. Active = white text + 2px F1 Red bottom border. Inactive = `#A1A1AA`.
- **Content:** centered max-width 1100px, 28px top / 48px bottom padding, 32px horizontal.

## Design Tokens

### Colors

```ts
// Surfaces
const bg            = "#100D0B"; // page background (warm black)
const cardBg        = "#0E0E10"; // card surfaces
const cardBgInner   = "#08080A"; // expanded-detail nested tables
const border        = "#1F1F23"; // hairline borders, dividers
const rowAlt        = "#0C0C0E"; // alternating table row

// Text
const fg            = "#FAFAFA"; // primary
const fgMuted       = "#A1A1AA"; // secondary copy
const fgDim         = "#71717A"; // labels, footnotes
const fgFaint       = "#52525B"; // rank numbers, axis ticks

// Accent
const accent        = "#E8002D"; // F1 Red — wordmark, active tab/pill, Oracle line/bar
const win           = "#34D399"; // positive P&L, edge up, WIN result
const loss          = "#F87171"; // negative P&L, edge down, LOSS result
const betBg         = "rgba(16,185,129,0.15)";
const betBorder     = "rgba(16,185,129,0.35)";
const betText       = "#34D399";
const betRowBg      = "rgba(16,185,129,0.06)";
const betRowBorder  = "#10B981";

// Pills / badges
const pillInactive  = "#18181B";
const pillBorder    = "#27272A";
const marketBadgeBg = "#27272A";
const marketBadgeFg = "#D4D4D8";
```

### Typography

- **UI font:** Geist Sans (load via `next/font/google` — already set up per brief)
- **Numbers:** Geist Mono with `font-variant-numeric: tabular-nums`
- **Letter-spacing:** −0.02em on H1/wordmark, −0.005em on tabs/labels, +0.04em on monospace abbreviations, +0.08–0.14em uppercase on tiny labels

| Role                | Family     | Size | Weight | Tracking  |
|---------------------|-----------|-----:|-------:|-----------|
| Page H1             | Geist     | 32px | 600    | -0.025em  |
| Wordmark            | Geist     | 26px | 800/600| -0.02em   |
| Stat value          | Geist Mono| 30px | 600    | -0.02em   |
| Stat label          | Geist     | 11px | 500    | 0.12em uppercase |
| Tab                 | Geist     | 14px | 400/500| -0.005em  |
| Body / row text     | Geist     | 13–14px | 400 | normal    |
| Driver abbrev       | Geist Mono| 13px | 700    | 0.04em    |
| Table header        | Geist     | 10px | 500    | 0.14em uppercase |
| Edge / mono numerals| Geist Mono| 12–13px | 600 | tabular   |

### Spacing & shape

- Container max-width: **1100px**, horizontal padding 32px
- Stat-card padding: `18px 20px` (regular density)
- Table cell padding: `12–16px × 20px`
- Border radius: **8px** cards, **6px** badges, **999px** pills/probability bars
- Probability bar: 90px × 6px, 999px radius
- Row dividers: 1px `#15151A`

## Components

The HTML prototype already organizes these as discrete components — recreate them as Tailwind/React components in the codebase:

| Prototype name | Purpose                                       |
|---------------|-----------------------------------------------|
| `Shell`        | Page chrome (wordmark, tabs, content slot)    |
| `StatCard`     | Label + big number + optional sub             |
| `Pill`         | Market-tab pill (active/inactive)             |
| `BetBadge`     | Emerald `BET` chip                            |
| `MarketBadge`  | `WIN` / `PODIUM` / `POLE` chip                |
| `ProbBar`      | 90×6 track + fill + right-aligned % label     |
| `Edge`         | `▲/▼ x.x%` colored, or `—` if `<2%`            |
| `SectionCard`  | Outer card container with hairline border     |

## Behavior

- **Tabs:** Next.js `<Link>` between `/`, `/season`, `/portfolio`. Active state = current pathname.
- **Market tabs (Race Weekend):** client component; switches between `Race Winner / Podium / Pole Position` markets fetched server-side.
- **Race accordion (Season Record):** click header to toggle expand. Default-expanded = most recent race. Single-expanded or multi-expanded — design supports either; recommend multi-expanded with most recent open by default.
- **No hover states beyond very subtle `#15151A` row lightening** — keep static.
- **No loading skeletons** — pages are RSC-rendered.

## Empty States

- Race Weekend (no predictions yet): centered card, `#71717A` text, `No predictions yet for this market. Run the model after qualifying.`
- Season Record (no settled races): `No settled bets yet. Season record will appear here after the first race.`
- Portfolio (first race pending): `Portfolio history will appear here after the first settled race.`

## Sample Data

Use the values shown in the prototype as exact fixtures while wiring up. They mirror the brief's listed examples and are calibrated to the chart range.

## Files in This Bundle

- `README.md` — this document
- `original-design-brief.md` — the brief that drove the design
- `F1 Oracle Mockups.html` — entry point; loads the canvas + all three pages with a Tweaks panel
- `design-canvas.jsx` — pan/zoom canvas component (prototype-only, not for production)
- `tweaks-panel.jsx` — tweaks chrome (prototype-only, not for production)
- `pages/shell.jsx` — shared `Shell` + `StatCard`, `Pill`, `BetBadge`, `MarketBadge`, `ProbBar`, `Edge`, `SectionCard` (recreate these as Tailwind components)
- `pages/race-weekend.jsx` — Race Weekend page reference
- `pages/season-record.jsx` — Season Record page reference
- `pages/portfolio.jsx` — Portfolio page reference (chart is custom SVG; production should use Recharts 3)

To preview locally: open `F1 Oracle Mockups.html` in a browser. Toggle the Tweaks panel to compare alternatives — but build to the **Final Design Decisions** values above.
