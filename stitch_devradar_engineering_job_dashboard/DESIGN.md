---
name: DevRadar Engineering Command
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353942'
  surface-container-lowest: '#0a0e16'
  surface-container-low: '#181c24'
  surface-container: '#1c2028'
  surface-container-high: '#262a33'
  surface-container-highest: '#31353e'
  on-surface: '#dfe2ee'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dfe2ee'
  inverse-on-surface: '#2c3039'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#d0bcff'
  on-tertiary: '#3c0091'
  tertiary-container: '#a078ff'
  on-tertiary-container: '#340080'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#0f131c'
  on-background: '#dfe2ee'
  surface-variant: '#31353e'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0em
  code-xs:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.25rem
  margin: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style
The design system establishes a high-performance command center tailored for senior software architects, AI researchers, and specialized systems engineers. Rooted in the visual precision of modern developer interfaces like Linear, Raycast, and Vercel, the design embraces dark-mode utility, structural clarity, and calibrated information density.

The aesthetic philosophy balances brutalist structural discipline with polished modern minimalism:
- **Atmospheric Void:** Deep blue-gray surfaces that reduce visual fatigue during marathon terminal sessions while preserving contrast.
- **Micro-interactions & Glows:** Restrained radial gradients, sub-pixel borders, and subtle luminescent accents that indicate real-time engine states and data freshness without decorative excess.
- **Technical Density:** Compact typography scales, tabular figures, and tightly clustered status indicators allow large volumes of telemetry and listings to be parsed rapidly without disorientation.

## Colors
The color architecture relies on a dark void foundation accented by domain-specific neon signals to deliver instant categorical recognition across complex data surfaces.

### Surfaces & Structure
- **Canvas / Void:** `#0B0F17` — Core application canvas.
- **Surface Level 1:** `#131B2A` — Primary containers, split panes, and grouped data grids.
- **Surface Level 2:** `#161F30` — Elevated cards, flyouts, and command palette inputs.
- **Surface Level 3 / Hover:** `#1E293B` — Interactive surface highlights, active rows, and dropdown panels.
- **Sub-pixel Borders:** `#1F2C42` (Base structural dividers) and `#26354D` (Card boundaries, active inputs, and elevated borders).

### Domain Accents
- **Primary / Focus:** `#3B82F6` (Electric Blue) — Primary action buttons, active navigation markers, keyboard shortcut focus rings, and live sync operations.
- **Silicon, AI & Compute:** `#10B981` (Emerald) and `#06B6D4` (Cyan) — CUDA/Triton tags, LLM inference pipelines, and neural compute engineering roles.
- **Graphics, Engine & Simulation:** `#8B5CF6` (Electric Violet) and `#A855F7` (Purple) — C++, Vulkan/DirectX, low-latency shaders, and real-time graphics tracks.
- **Regional & Infrastructure Nodes:** `#F59E0B` (Amber Gold) — Cloud architecture clusters, distributed infrastructure, and regional engineering hubs.

### Functional States
- **Text Primary:** `#F8FAFC`
- **Text Secondary / Muted:** `#94A3B8`
- **Text Tertiary / Ghost:** `#64748B`
- **Critical / Drop / Error:** `#EF4444`

## Typography
The system enforces a dual-type architecture:
- **Inter** governs primary human-facing UI, structural headings, narrative specifications, and interactive labels. Tight tracking curves ensure crisp legibility on high-DPI displays.
- **JetBrains Mono** handles all metrics, compensation ranges, timestamp telemetry, hotkey shortcuts, stack tags, and raw pipeline outputs. Tabular figures (`tnum`) must remain enabled across all monospaced numerical displays to prevent layout jitter during live socket feeds.

## Layout & Spacing
The layout model employs an adaptive 12-column fluid grid framework with fixed-width utility rail configurations.

### Grid & Breakpoints
- **Desktop (>= 1280px):** 12-column layout with 20px (`1.25rem`) gutters and 32px (`2rem`) edge canvas margins. Accommodates three distinct work zones: 240px collateral filter rail, 480px scrollable tracker stream, and flex dynamic telemetry inspector pane.
- **Tablet (768px - 1279px):** 8-column layout with 16px (`1rem`) gutters and 24px margins. Inspector pane docks into an off-canvas slide-over triggered by keyboard hotkey or focus click.
- **Mobile (< 768px):** 4-column layout with 12px gutters and 16px margins. Transforms into a single-column stacked view with top-level pill-filtered navigation and sticky bottom command triggers.

### Spacing Discipline
All internal padding and item spacing follow strict 4px base multiples. Vertical list spacing in high-density streams uses `space-xs` (4px) to `space-sm` (8px) gaps to maximize data per viewport.

## Elevation & Depth
Depth is produced primarily through tonal layering, sub-pixel interior borders, and targeted luminescent backdrops rather than conventional heavy drop shadows.

### Layer Tiers
- **Tier 0 (Base Canvas):** Solid `#0B0F17`.
- **Tier 1 (Surface Panels):** Background `#131B2A` with a 1px solid `#1F2C42` border.
- **Tier 2 (Floating & Focused Cards):** Background `#161F30` with a 1px border `#26354D` and a subtle inner top highlight (`inset 0 1px 0 0 rgba(255, 255, 255, 0.05)`).
- **Tier 3 (Modals, Command Overlay & Dropdowns):** Background `#161F30`, 1px border `#3B82F6` (at 40% alpha), elevated with an ambient glow shadow: `0 16px 40px -12px rgba(0, 0, 0, 0.7), 0 0 24px -4px rgba(59, 130, 246, 0.12)`.

### Ambient Glows
Live states (such as active telemetry ingestion or newly matched roles) apply soft, localized radial gradients behind badges and card corners using their respective category accent colors at 8–12% opacity with a 24px blur radius.

## Shapes
The design adopts a sharp, technical contour language (`roundedness: 1`):
- **Base Components:** Inputs, tags, dropdown triggers, and buttons use 4px (`0.25rem`) border radiuses.
- **Structural Cards & Panels:** Card containers and dashboard tiles use 8px (`0.5rem`) radiuses to retain industrial precision without harshness.
- **Pills / Status Dots:** Circular status indicators and hotkey keycaps utilize full rounding only where necessary to distinguish them from tabular data frames.

## Components

### Buttons
- **Primary Sync CTA:** `#3B82F6` solid fill, `#F8FAFC` semibold text, 1px top highlight (`rgba(255,255,255,0.2)`). Hover: `#2563EB` with an ambient `0 0 16px rgba(59, 130, 246, 0.35)` glow.
- **Secondary Ghost:** Transparent background, 1px `#1F2C42` border, `#94A3B8` text. Hover: `#161F30` background, `#26354D` border, `#F8FAFC` text.
- **Hotkey Action Button:** Surface `#131B2A`, inline monospaced hotkey tag (`KBD`) rendered with `#1E293B` background and `#64748B` border.

### Status Chips & Category Badges
- Rendered in `code-sm` typography using `JetBrains Mono`.
- Built with a 10% opacity background of the accent color, a matching 1px border at 25% opacity, and full brightness foreground text.
- **AI / Compute:** `#10B981` tint with a flashing 6px live radar beacon dot.
- **Graphics / Game Dev:** `#8B5CF6` tint.
- **Infra / MENA Cloud:** `#F59E0B` tint.

### Data Cards & Job Stream Tiles
- Background `#131B2A`, border 1px `#1F2C42`, radius 8px (`0.5rem`).
- Left-edge 2px vertical accent strip indicates category specialization.
- Hover state transitions border to `#26354D` and lifts background to `#161F30` with zero layout shift.
- Inner metadata grid uses monospaced figures for compensation, ping latency, and role creation delta (`2m ago`, `14ms`).

### Inputs & Terminal Search
- Background `#0B0F17`, 1px solid border `#1F2C42`, text `#F8FAFC`.
- Focus ring: 1px border `#3B82F6` and an ambient focus shadow `0 0 0 1px #3B82F6, 0 0 12px rgba(59, 130, 246, 0.25)`.
- Pre-appended with a monospaced terminal prompt prefix (`> `) in `#64748B`.

### Lists & Telemetry Feeds
- Zebra-free layout relying on 1px horizontal dividers (`#1F2C42`).
- Compact table rows: 36px height; standard rows: 48px height.
- Interactive hover: instant background tint to `#161F30` with trailing keyboard navigation indicator (`↵`).

### Checkboxes & Segmented Controls
- Checkboxes: 16x16px boxes with 1px border `#26354D` and background `#0B0F17`. Checked state triggers `#3B82F6` fill with an angled white checkmark icon.
- Segmented switches: Contained `#0B0F17` track with a sliding `#161F30` 1px-bordered tab indicator.